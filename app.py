import os
from tkinter import Image
import PyPDF2
from fpdf import FPDF
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
import pytesseract
import requests
from werkzeug.utils import secure_filename
import logging
from dotenv import load_dotenv
from openai import OpenAI
import json
import sys
import tempfile
from groq import Groq

# app = Flask(__name__)
app = Flask(__name__, static_folder='static')

# Configure logging
logging.basicConfig(level=logging.INFO)

# Add debug logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ocr_debug.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'png', 'jpg', 'jpeg'}

# groqcloud API Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
MODEL_NAME = "llama-3.3-70b-versatile"
SCRIPTS_METADATA_FILE = 'saved_scripts/scripts_metadata.json'

# Initialize groqcloud client
client = Groq(
    api_key=GROQ_API_KEY,
)

# Create required directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('saved_scripts', exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/static/examples/<path:filename>')
def serve_example(filename):
    """Serve example files from the static/examples directory"""
    return send_from_directory('static/examples', filename)

def check_ocr_installation():
    """Check if Tesseract OCR is properly installed and configured"""
    try:
        version = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract OCR version: {version}")
        return True
    except Exception as e:
        logger.error(f"Tesseract OCR not properly installed: {str(e)}")
        return False

def validate_image(image_path):
    """Validate image file and check if it's suitable for OCR"""
    try:
        with Image.open(image_path) as img:
            # Check image size
            width, height = img.size
            if width < 50 or height < 50:
                logger.warning(f"Image too small: {width}x{height}")
                return False, "Image too small for OCR"
            
            # Check image mode
            if img.mode not in ['L', 'RGB']:
                logger.warning(f"Unsupported image mode: {img.mode}")
                return False, "Unsupported image format"
            
            # Check file size
            file_size = os.path.getsize(image_path) / (1024 * 1024)  # Size in MB
            if file_size > 10:
                logger.warning(f"Image file too large: {file_size:.2f}MB")
                return False, "File size too large"
            
            return True, "Image valid for OCR"
    except Exception as e:
        logger.error(f"Image validation error: {str(e)}")
        return False, str(e)

def extract_text_from_image(image_path):
    """Extract text from image using OCR with enhanced debugging"""
    try:
        # Check OCR installation first
        if not check_ocr_installation():
            return "OCR not available"

        # Validate image
        is_valid, message = validate_image(image_path)
        if not is_valid:
            logger.error(f"Image validation failed: {message}")
            return f"Image validation failed: {message}"

        # Log OCR attempt
        logger.info(f"Starting OCR processing for: {image_path}")
        
        # Open and preprocess image
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode not in ['L', 'RGB']:
                img = img.convert('RGB')
            
            # Create temporary file for processed image
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                img.save(tmp_file.name, 'PNG')
                logger.debug(f"Saved preprocessed image to: {tmp_file.name}")
                
                # Perform OCR
                text = pytesseract.image_to_string(tmp_file.name)
                
                # Clean up temporary file
                os.unlink(tmp_file.name)

        # Validate OCR result
        if not text.strip():
            logger.warning("OCR produced no text")
            return "No text detected in image"

        logger.info(f"OCR successful - extracted {len(text)} characters")
        return text.strip()

    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}", exc_info=True)
        return f"OCR Error: {str(e)}"

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        logging.error(f"Error in PDF processing: {str(e)}")
        return ""

def process_file_content(file):
    """Process uploaded files with enhanced error handling and logging"""
    if not file or not allowed_file(file.filename):
        logger.warning(f"Invalid file or filename: {getattr(file, 'filename', 'No file')}")
        return ""

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        logger.info(f"File saved successfully: {filepath}")
        
        file_type = filename.rsplit('.', 1)[1].lower()
        
        # Process different file types
        if file_type in ['jpg', 'jpeg', 'png']:
            logger.info(f"Processing image file: {filename}")
            ocr_result = extract_text_from_image(filepath)
            
            if ocr_result.startswith(("OCR Error:", "Image validation failed:", "No text detected")):
                logger.warning(f"OCR processing issue: {ocr_result}")
                return filepath  # Return path for image processing
            
            logger.info("OCR processing successful")
            return f"OCR Extract:\n{ocr_result}"
            
        elif file_type == 'pdf':
            file_content = extract_text_from_pdf(filepath)
            return f"PDF Extract:\n{file_content}"
        
        else:  # For text files
            with open(filepath, 'r', encoding='utf-8') as f:
                file_content = f.read()
        
        # Clean up the uploaded file
        os.remove(filepath)
        return file_content
            
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        if os.path.exists(filepath):
            os.remove(filepath)
        return ""

def generate_script_with_xai(prompt, image_path=None, additional_context=""):
    try:
        messages = []
        
        # Add system message
        messages.append({
            "role": "system",
            "content": "You are a professional video script writer. Create engaging and well-structured video scripts."
        })

        # If there's an image, add it to the messages
        if (image_path):
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_path,
                            "detail": "high",
                        },
                    },
                    {
                        "type": "text",
                        "text": f"{prompt}\n\nAdditional Context:\n{additional_context}".strip(),
                    },
                ],
            })
        else:
            # Text-only prompt
            messages.append({
                "role": "user",
                "content": f"{prompt}\n\nAdditional Context:\n{additional_context}".strip()
            })

        # Make the API call
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7,
        )

        return {
            "success": True,
            "script": completion.choices[0].message.content
        }

    except Exception as e:
        logging.error(f"Error calling X.ai API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_script', methods=['POST'])
def generate_script():
    try:
        # Get prompt from form
        prompt = request.form.get('prompt', '').strip()
        if not prompt:
            return jsonify({"success": False, "error": "No prompt provided"}), 400

        # Process uploaded file if any
        image_path = None
        file_content = ""
        if 'file' in request.files and request.files['file'].filename:
            result = process_file_content(request.files['file'])
            if isinstance(result, str):
                if result.startswith(('OCR Extract:', 'PDF Extract:')):
                    file_content = result
                else:
                    file_content = result[:4000]  # Limit file content
            else:
                image_path = result

        # Process URL if provided
        url_content = ""
        url = request.form.get('url', '').strip()
        if url:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                url_response = requests.get(url, headers=headers, timeout=10)
                url_response.raise_for_status()

                # Extract main content and limit its size
                content = url_response.text

                # Then replace the content cleaning part with:
                soup = BeautifulSoup(content, 'html.parser')
                # Remove scripts, styles, and other unnecessary elements
                for element in soup(['script', 'style', 'meta', 'link']):
                    element.decompose()
                content = soup.get_text(separator=' ', strip=True)
                
                # Limit content length
                max_content_length = 4000  # Adjust this value as needed
                if len(content) > max_content_length:
                    content = content[:max_content_length] + "..."
                
                url_content = f"Reference URL ({url}):\n{content}"

            except requests.RequestException as e:
                logging.warning(f"Error fetching URL content: {str(e)}")
                url_content = f"Reference URL: {url}"

        # Combine additional context with length limits
        additional_context = ""
        if file_content:
            additional_context += f"File Content:\n{file_content[:2000]}\n\n"  # Limit file content
        if url_content:
            additional_context += f"{url_content[:2000]}\n\n"  # Limit URL content

        # Ensure total prompt length is within limits
        max_prompt_length = 4000  # Adjust based on model's requirements
        combined_prompt = f"{prompt}\n\nAdditional Context:\n{additional_context}".strip()
        if len(combined_prompt) > max_prompt_length:
            # Prioritize the main prompt and trim additional context
            available_length = max_prompt_length - len(prompt) - 100  # Leave some buffer
            if available_length > 0:
                additional_context = additional_context[:available_length] + "..."
            else:
                additional_context = ""

        # Generate script using X.ai API
        result = generate_script_with_xai(prompt, image_path, additional_context)
        
        # Clean up image file if it exists
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 500

    except Exception as e:
        logging.error(f"Error in generate_script: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def extract_title(title_text):
    """
    Extract only the first sentence as the title, handling multiple sentence endings.
    """
    if not title_text:
        return "Untitled Script"
    
    # List of sentence endings to check
    sentence_endings = ['. ', '! ', '? ', '... ', '। ', '॥ ', '؟ ']
    
    # Clean the input text first
    cleaned_text = title_text.replace('\n', ' ').replace('\r', ' ').strip()
    
    # Find the first sentence ending
    first_sentence_end = float('inf')
    for ending in sentence_endings:
        pos = cleaned_text.find(ending)
        if pos != -1 and pos < first_sentence_end:
            first_sentence_end = pos
    
    # Extract the first sentence
    if first_sentence_end != float('inf'):
        title = cleaned_text[:first_sentence_end].strip()
    else:
        # If no sentence ending found, use the whole text up to a reasonable length
        title = cleaned_text[:100].strip()  # Limit to 100 characters if no sentence end found
    
    # Additional cleaning
    # Remove common prefixes that might appear
    prefixes_to_remove = ['Introduction:', 'Intro:', 'Title:', 'Topic:']
    for prefix in prefixes_to_remove:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()
    
    # If title is too short, use a reasonable part of the text
    if len(title) < 3:
        title = cleaned_text[:50].strip()  # Use first 50 characters
    
    # Final length check
    if len(title) > 100:
        title = title[:97] + "..."
    
    return title or "Untitled Script"

def save_script_metadata(filename, script_data):
    try:
        metadata = []
        if os.path.exists(SCRIPTS_METADATA_FILE):
            with open(SCRIPTS_METADATA_FILE, 'r') as f:
                metadata = json.load(f)
        
        # Get the raw title from the first section or script data
        raw_title = ''
        sections = script_data.get('metadata', {}).get('unformatted_sections', [])
        if sections and sections[0].get('content'):
            raw_title = sections[0]['content'][0]
        else:
            raw_title = script_data.get('title', '')
        
        # Extract just the first sentence as title
        title = extract_title(raw_title)
        
        # Create new metadata entry with current timestamp
        new_entry = {
            'filename': filename,
            'title': title,
            'timestamp': datetime.now().isoformat(),  # Always use current time
            'preview': script_data.get('script', '')[:200] + '...' if len(script_data.get('script', '')) > 200 else script_data.get('script', ''),
            'sections': script_data.get('metadata', {}).get('unformatted_sections', []),
            'formatted_html': script_data.get('metadata', {}).get('formatted_html', '')
        }
        
        # Insert at the beginning of the list
        metadata.insert(0, new_entry)
        
        with open(SCRIPTS_METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving metadata: {str(e)}")

@app.route('/saved_scripts')
def view_saved_scripts():
    try:
        if os.path.exists(SCRIPTS_METADATA_FILE):
            with open(SCRIPTS_METADATA_FILE, 'r') as f:
                metadata = json.load(f)
                # Sort metadata by timestamp in descending order (newest first)
                metadata.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return render_template('saved_scripts.html', scripts=metadata)
        return render_template('saved_scripts.html', scripts=[])
    except Exception as e:
        logging.error(f"Error loading saved scripts: {str(e)}")
        return render_template('saved_scripts.html', scripts=[], error=str(e))

@app.route('/download_script/<filename>')
def download_script(filename):
    try:
        return send_from_directory('saved_scripts', filename, as_attachment=True)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 404

def parse_html_content(formatted_html):
    """Parse HTML content and extract structured content"""
    soup = BeautifulSoup(formatted_html, 'html.parser')
    content_structure = []
    
    # Find all direct children of the main div
    main_div = soup.find('div', class_='space-y-6')
    if (main_div):
        for element in main_div.children:
            if element.name == 'h3':
                # Extract section headers
                dot_span = element.find('span', class_='bg-blue-600')
                text_span = element.find_all('span')[-1]
                content_structure.append({
                    'type': 'header',
                    'content': text_span.get_text().strip()
                })
            elif element.name == 'p':
                # Extract paragraphs with formatting
                formatted_text = ''
                for child in element.children:
                    if child.name == 'strong':
                        formatted_text += f'<b>{child.get_text()}</b>'
                    elif child.name == 'i':
                        formatted_text += f'<i>{child.get_text()}</i>'
                    else:
                        formatted_text += str(child)
                content_structure.append({
                    'type': 'paragraph',
                    'content': formatted_text.strip()
                })
    
    return content_structure

def create_styled_pdf(content_structure, filepath):
    """Create PDF with consistent margins and padding"""
    # A4 size in mm: 210 x 297
    margin = 20  # Consistent margin of 20mm on all sides
    
    pdf = FPDF(format='A4')
    # Set consistent margins (left, top, right) in mm
    pdf.set_margins(margin, margin, margin)
    # Set auto page break with bottom margin
    pdf.set_auto_page_break(True, margin)
    
    pdf.add_page()
    
    # Calculate effective page width (A4 width - margins)
    effective_width = 210 - (2 * margin)
    
    # Add title with proper positioning
    pdf.set_font("Arial", 'B', 24)
    title_height = 15
    pdf.cell(effective_width, title_height, "Generated Video Script", ln=True, align='C')
    pdf.ln(5)
    
    # Add timestamp with proper alignment
    pdf.set_font("Arial", 'I', 11)
    pdf.set_text_color(100, 100, 100)
    timestamp_text = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    pdf.cell(effective_width, 8, timestamp_text, ln=True, align='R')
    pdf.ln(10)
    
    # Reset text color
    pdf.set_text_color(0, 0, 0)
    
    # Process content with consistent spacing
    for item in content_structure:
        if item['type'] == 'header':
            pdf.set_font("Arial", 'B', 14)
            # Add section header with consistent indentation
            pdf.cell(6, 10, "-", 0, 0, 'R')  # Bullet point
            try:
                header_text = item['content'].encode('latin-1', 'ignore').decode('latin-1')
                pdf.multi_cell(effective_width - 6, 10, header_text, 0)
            except Exception:
                header_text = item['content'].encode('ascii', 'ignore').decode('ascii')
                pdf.multi_cell(effective_width - 6, 10, header_text, 0)
            pdf.ln(2)
            
        elif item['type'] == 'paragraph':
            pdf.set_font("Arial", '', 12)
            text = item['content']
            
            if '<' in text:  # Handle formatted text
                parts = text.split('<')
                line_height = pdf.font_size * 1.5
                current_y = pdf.get_y()
                
                formatted_text = ''
                for part in parts:
                    if not part:
                        continue
                    
                    if part.startswith('b>'):
                        formatted_text += part[2:].split('</b>')[0]
                    elif part.startswith('i>'):
                        formatted_text += part[2:].split('</i>')[0]
                    else:
                        formatted_text += str(part)
                
                try:
                    safe_text = formatted_text.encode('latin-1', 'ignore').decode('latin-1')
                    pdf.multi_cell(effective_width, line_height, safe_text)
                except Exception:
                    safe_text = formatted_text.encode('ascii', 'ignore').decode('ascii')
                    pdf.multi_cell(effective_width, line_height, safe_text)
            else:
                try:
                    safe_text = text.encode('latin-1', 'ignore').decode('latin-1')
                    pdf.multi_cell(effective_width, 8, safe_text)
                except Exception:
                    pdf.multi_cell(effective_width, 8, text.encode('ascii', 'ignore').decode('ascii'))
            
            pdf.ln(4)
    
    try:
        # Add page numbers at the bottom with consistent margins
        page_numbers = pdf.page_no()
        for page in range(1, page_numbers + 1):
            pdf.page = page
            pdf.set_y(-margin - 10)  # Position 10mm above bottom margin
            pdf.set_font('Arial', 'I', 8)
            pdf.cell(effective_width, 10, f'Page {page}/{page_numbers}', 0, 0, 'C')
        
        pdf.output(filepath)
    except Exception as e:
        logging.error(f"Error in PDF generation: {str(e)}")
        pdf = FPDF(format='A4')
        pdf.set_margins(margin, margin, margin)
        pdf.set_auto_page_break(True, margin)
        pdf.add_page()
        
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(effective_width, 10, "Generated Video Script", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        
        for item in content_structure:
            text = item['content'].encode('ascii', 'ignore').decode('ascii')
            pdf.multi_cell(effective_width, 10, text)
            pdf.ln(5)
        
        pdf.output(filepath)

@app.route('/save_script', methods=['POST'])
def save_script():
    try:
        script_data = request.get_json()
        formatted_html = script_data.get('metadata', {}).get('formatted_html', '')
        
        if not formatted_html:
            return jsonify({"success": False, "error": "No formatted content provided"}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{timestamp}_script.pdf'
        filepath = os.path.join('saved_scripts', filename)

        if not os.path.exists('saved_scripts'):
            os.makedirs('saved_scripts')

        content_structure = parse_html_content(formatted_html)
        
        create_styled_pdf(content_structure, filepath)
        
        save_script_metadata(filename, script_data)

        return jsonify({
            "success": True,
            "filename": filename
        })

    except Exception as e:
        logging.error(f"Error saving script: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/get_script_content/<filename>')
def get_script_content(filename):
    try:
        script_path = os.path.join('saved_scripts', filename)
        if not os.path.exists(script_path):
            return jsonify({"success": False, "error": "Script not found"}), 404

        with open(SCRIPTS_METADATA_FILE, 'r') as f:
            metadata = json.load(f)
            
        script_data = next((s for s in metadata if s['filename'] == filename), None)
        if not script_data:
            return jsonify({"success": False, "error": "Metadata not found"}), 404

        return jsonify({
            "success": True,
            "content": script_data['formatted_html'],
            "title": script_data['title']
        })

    except Exception as e:
        logging.error(f"Error getting script content: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/delete_script/<filename>', methods=['DELETE'])
def delete_script(filename):
    try:
        script_path = os.path.join('saved_scripts', filename)
        if os.path.exists(script_path):
            os.remove(script_path)

        # Update metadata
        with open(SCRIPTS_METADATA_FILE, 'r') as f:
            metadata = json.load(f)
        
        metadata = [s for s in metadata if s['filename'] != filename]
        
        with open(SCRIPTS_METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)

        return jsonify({"success": True})

    except Exception as e:
        logging.error(f"Error deleting script: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Add template filter for datetime formatting
@app.template_filter('datetime')
def format_datetime(value):
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime('%B %d, %Y at %I:%M %p')
    except:
        return value

@app.errorhandler(413)
def too_large(e):
    return jsonify({
        "success": False,
        "error": "File is too large"
    }), 413

@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500

if __name__ == "__main__":
    app.run(debug=True)
