const scriptForm = document.getElementById('scriptForm');
const loading = document.getElementById('loading');
const results = document.getElementById('results');
const scriptContent = document.getElementById('scriptContent');
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toastMessage');

function showToast(type, message, duration = 3000) {
    const toasts = document.querySelectorAll('.toast-success, .toast-error, .toast-info, .toast-warning');
    toasts.forEach(t => t.classList.add('hidden'));
    
    const targetToast = document.querySelector(`.toast-${type}`);
    if (targetToast) {
        targetToast.classList.remove('hidden');

        const typeSpecificMessage = targetToast.querySelector(`#toast${type.charAt(0).toUpperCase() + type.slice(1)}Message`);
        if (typeSpecificMessage) {
            typeSpecificMessage.textContent = message;
        }
        
        if (toastMessage) {
            toastMessage.textContent = message;
        }
    }

    toast.classList.add('toast-show');
    toast.classList.remove('toast-hide');

    if (duration > 0) {
        setTimeout(hideToast, duration);
    }
}

function hideToast() {
    const toast = document.getElementById('toast');
    toast.classList.remove('toast-show');
    toast.classList.add('toast-hide');
}

// Add necessary CSS
const style = document.createElement('style');
style.textContent = `
    .toast-show {
        transform: translateY(0) !important;
        opacity: 1 !important;
    }
    .toast-hide {
        transform: translateY(100%) !important;
        opacity: 0 !important;
    }
`;
document.head.appendChild(style);

function updateFileName(input) {
    const fileName = input.files[0]?.name || 'Drop file here or click to upload';
    document.getElementById('fileName').textContent = fileName;
  }
  
function formatScript(script) {
    const sections = [];
    script = script.replace(/\[([^\]]+)\]/g, (match, content) => {
        sections.push(content);
        return `###SECTION${sections.length - 1}###`;
    });

    let formattedScript = script
        .replace(/(?<!\*)\*(?!\*)/g, '')     // Remove standalone asterisks (not part of formatting)
        .replace(/(?<!\*)\*\*(?!\*)/g, '')  // Remove standalone double asterisks
        .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-bold text-gray-800">$1</strong>') // Format bold text
        .replace(/\*([^*]+)\*/g, '<i class="italic text-gray-800">$1</i>')  // Format italic text
        .replace(/\n\n/g, '</p><p class="mb-4">')   // Handle line breaks
        .replace(/\n/g, '<br>')
        .trim();

    // Restore sections with proper formatting
    sections.forEach((section, index) => {
        formattedScript = formattedScript.replace(
            `###SECTION${index}###`,
            `<h3 class="text-xl font-bold text-gray-800 mt-6 mb-3 flex items-center">
                <span class="w-1.5 h-1.5 bg-blue-600 rounded-full mr-2"></span>
                <span>${section}</span>
            </h3>`
        );
    });

    formattedScript = `<p class="mb-4">${formattedScript}</p>`;
    return formattedScript;
}

scriptForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    loading.classList.remove('hidden');
    results.classList.add('hidden');

    const formData = new FormData(scriptForm);

    try {
        const response = await axios.post('/generate_script', formData);
        
        if (response.data.success) {
            const formattedScript = formatScript(response.data.script);
            scriptContent.innerHTML = `
                <div class="space-y-6">
                    ${formattedScript}
                </div>
            `;
            
            const paragraphs = scriptContent.querySelectorAll('p');
            paragraphs.forEach(p => {
                p.classList.add('text-gray-700', 'leading-relaxed', 'text-lg');
            });

            // Clean up any remaining markdown artifacts
            scriptContent.innerHTML = scriptContent.innerHTML
                .replace(/\\\*/g, '*') // Restore escaped asterisks
                .replace(/\s*\*\s*/g, '') // Remove any remaining standalone asterisks
                .replace(/\s{2,}/g, ' '); // Clean up extra spaces

            results.classList.remove('hidden');
            showToast('success', 'Script generated successfully!');
        } else {
            showToast('error', 'Error generating script: ' + response.data.error);
        }
    } catch (error) {
        showToast('error', 'Error: ' + (error.response?.data?.error || error.message));
    } finally {
        loading.classList.add('hidden');
    }
});

// Improved copy function that cleans up the text
async function copyScript() {
    try {
        let plainText = scriptContent.innerText
            .replace(/\s*\*\s*/g, '') // Remove standalone asterisks
            .replace(/\n\s*\n/g, '\n\n') // Fix double line breaks
            .replace(/\s{2,}/g, ' ') // Clean up extra spaces
            .trim();
        
        await navigator.clipboard.writeText(plainText);
        showToast('success', 'Script copied to clipboard!');
    } catch (err) {
        showToast('error', 'Failed to copy script');
    }
}

// Save function with cleaned text and title
async function saveScript() {
    try {
        // Get both formatted and unformatted versions
        let cleanText = scriptContent.innerText
            .replace(/\s*\*\s*/g, '')
            .replace(/\s{2,}/g, ' ')
            .trim();

        let formattedHtml = scriptContent.innerHTML;
        let unformattedSections = getUnformattedScript(cleanText);
        let title = unformattedSections[0]?.content[0] || 'Untitled Script';

        const scriptData = {
            script: cleanText,
            title: title,
            metadata: {
                formatted_html: formattedHtml,
                unformatted_sections: unformattedSections,
                timestamp: new Date().toISOString(),
                version: "1.0"
            }
        };

        const response = await axios.post('/save_script', scriptData);
        
        if (response.data.success) {
            showToast('success', 'Script saved successfully!');
            setTimeout(() => {
                showToast('info', 'Click "View Saved" to see all scripts', 5000);
            }, 3000);
        } else {
            showToast('error', 'Error saving script: ' + response.data.error);
        }
    } catch (error) {
        showToast('error', 'Error: ' + (error.response?.data?.error || error.message));
    }
}

// File name update function
function updateFileName(input) {
    const fileName = input.files[0]?.name || 'Drop file here or click to upload';
    document.getElementById('fileName').textContent = fileName;
}

// Function to get unformatted script
function getUnformattedScript(script) {
    // Remove HTML tags and clean up the text
    let unformattedText = script.replace(/<[^>]+>/g, '')
        .replace(/\s*\*\s*/g, '')
        .replace(/\s{2,}/g, ' ')
        .trim();
    
    let sections = [];
    let currentSection = {
        title: '',
        content: []
    };
    
    const lines = unformattedText.split('\n');
    lines.forEach(line => {
        line = line.trim();
        if (!line) return;

        if (line.toUpperCase() === line && line.length > 0) {
            if (currentSection.title) {
                sections.push({ ...currentSection });
            }
            currentSection = {
                title: line,
                content: []
            };
        } else {
            if (!currentSection.title) {
                currentSection.title = 'INTRODUCTION';
            }
            currentSection.content.push(line);
        }
    });

    if (currentSection.title && currentSection.content.length > 0) {
        sections.push(currentSection);
    }

    return sections;
}

// Function to download and upload example file
async function downloadAndUploadExample(filename) {
    try {
        const response = await fetch(`/static/examples/${filename}`);
        const blob = await response.blob();
        
        const file = new File([blob], filename, { type: blob.type });
        
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        
        const fileInput = document.getElementById('file');
        fileInput.files = dataTransfer.files;
        
        updateFileName(fileInput);
        
        showToast('success', `Example file "${filename}" loaded successfully!`);
    } catch (error) {
        console.error('Error downloading example:', error);
        showToast('error', 'Error loading example file');
    }
}

// Function to use example URL
function useExampleUrl(url, description) {
    const urlInput = document.getElementById('url');
    urlInput.value = url;
    urlInput.focus();
    
    urlInput.classList.add('ring-2', 'ring-green-500');
    setTimeout(() => {
        urlInput.classList.remove('ring-2', 'ring-green-500');
    }, 1000);
    
    showToast('success', `${description} URL loaded!`, 2000);
}