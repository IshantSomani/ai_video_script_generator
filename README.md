# AI Video Script Generator

This project is an AI-powered video script generator that allows users to create, save, and manage video scripts. The application uses OpenAI's API to generate scripts based on user prompts, reference files, and URLs. It also supports OCR for extracting text from images and PDFs.

## Features

- Generate video scripts using AI based on user prompts.
- Upload reference files (text, PDF, images) to enhance script generation.
- Provide reference URLs for additional context.
- Save generated scripts as PDF files.
- View, download, and delete saved scripts.
- Toast notifications for user feedback.

## Tech Stack

### Frontend
- HTML5, CSS3, JavaScript
- TailwindCSS for styling
- Font Awesome for icons
- Axios for HTTP requests
- Marked.js for Markdown rendering

### Backend
- Python 3.9+
- Flask web framework
- OpenAI API for script generation
- PyTesseract for OCR
- FPDF for PDF generation
- BeautifulSoup4 for HTML parsing

### Storage
- Local file system for script storage
- JSON for metadata management

## Key Features Implemented

### 1. Advanced Script Generation
- AI-powered script generation using OpenAI's API
- Multi-modal input support:
  - Text prompts
  - Image uploads (with OCR)
  - PDF document parsing
  - URL content extraction
- Context-aware script generation combining multiple inputs

### 2. File Processing
- OCR (Optical Character Recognition) for images
- PDF text extraction
- URL content scraping
- Support for multiple file formats:
  - Images (jpg, jpeg, png)
  - Documents (pdf, txt)
  - Web content (URLs)

### 3. Script Management
- Automatic script formatting
- PDF generation with professional styling
- Script metadata tracking
- Script preview functionality
- Download capabilities
- Delete operations

### 4. User Interface
- Responsive design for all devices
- Real-time loading indicators
- Toast notifications for user feedback
- Modal dialogs for script viewing
- Drag-and-drop file upload
- Example prompts and references

### 5. Error Handling
- Comprehensive error reporting
- File validation
- Size limit enforcement
- API error management
- OCR validation

## Project Structure
```
ai_video_script_generator/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
├── static/
│   ├── css/
│   │   └── styles.css         # Custom styles
│   ├── js/
│   │   └── main.js            # Frontend JavaScript
│   ├── examples/              # Example files
│   └── img/                   # Images and assets
├── templates/
│   ├── base.html              # Base template
│   ├── index.html             # Main page
│   ├── saved_scripts.html     # Saved scripts page
│   └── components/
│       └── toast.html         # Toast notification component
├── uploads/                   # Temporary file storage
└── saved_scripts/             # Storage for generated scripts
    └── scripts_metadata.json  # Metadata of saved scripts
```

## Setup and Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)
- Virtual environment (optional but recommended)

### Installation Steps

1. **Clone the repository:**

    ```bash
    git clone https://github.com/IshantSomani/ai_video_script_generator.git
    cd ai_video_script_generator
    ```

2. **Create and activate a virtual environment (optional but recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. **Install the required dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Set up environment variables:**

    Create a `.env` file in the project root directory and add your OpenAI API key:

    ```env
    XAI_API_KEY=your_openai_api_key
    ```

5. **Run the application:**

    ```bash
    python app.py
    ```

6. **Access the application:**

    Open your web browser and navigate to `http://127.0.0.1:5000`.

## Usage

1. **Generate a Script:**
    - Enter a script prompt in the provided text area.
    - Optionally, upload a reference file or provide a reference URL.
    - Click the "Generate Script" button to create a script.

2. **View and Manage Scripts:**
    - Navigate to the "Saved Scripts" page to view all saved scripts.
    - Use the "View", "Download", and "Delete" buttons to manage scripts.

3. **Toast Notifications:**
    - The application provides feedback through toast notifications for actions like script generation, saving, and errors.

## Limitations

- **File Size Limit:** The maximum file size for uploads is 16MB.
- **OCR Accuracy:** The accuracy of OCR depends on the quality of the uploaded images.
- **API Rate Limits:** The application relies on OpenAI's API, which may have rate limits and usage restrictions.
- **Content Length:** The combined length of the prompt and additional context is limited to 4000 characters.

## Troubleshooting

- **File Too Large:** Ensure that the uploaded file is within the 16MB limit.
- **OCR Errors:** Check that Tesseract OCR is properly installed and configured.
- **API Errors:** Verify that the OpenAI API key is correctly set in the `.env` file.

## Contributing

Contributions are welcome! Please fork the repository and submit pull requests for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.