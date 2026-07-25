// DOM Elements
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const removeFileBtn = document.getElementById('removeFile');
const analyzeBtn = document.getElementById('analyzeBtn');
const jobDescription = document.getElementById('jobDescription');
const resultsSection = document.getElementById('resultsSection');
const loading = document.getElementById('loading');
const resultsContent = document.getElementById('resultsContent');

let selectedFile = null;

// Upload box click handler
uploadBox.addEventListener('click', () => {
    fileInput.click();
});

// File input change handler
fileInput.addEventListener('change', (e) => {
    handleFile(e.target.files[0]);
});

// Drag and drop handlers
uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('drag-over');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('drag-over');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('drag-over');
    handleFile(e.dataTransfer.files[0]);
});

// Handle file selection
function handleFile(file) {
    if (!file) return;

    const validTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'image/jpeg',
        'image/png',
        'image/jpg'
    ];

    if (!validTypes.includes(file.type)) {
        alert('Please upload a PDF, DOCX, or image file');
        return;
    }

    selectedFile = file;
    
    // Display file info
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    
    uploadBox.style.display = 'none';
    fileInfo.style.display = 'flex';
    analyzeBtn.disabled = false;
}

// Remove file handler
removeFileBtn.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = '';
    uploadBox.style.display = 'block';
    fileInfo.style.display = 'none';
    analyzeBtn.disabled = true;
    resultsSection.style.display = 'none';
});

// Analyze button handler
analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    // Show results section with loading
    resultsSection.style.display = 'block';
    loading.style.display = 'block';
    resultsContent.style.display = 'none';
    resultsContent.innerHTML = '';

    try {
        // Convert file to base64
        const base64Data = await fileToBase64(selectedFile);
        const fileType = getFileExtension(selectedFile.name);

        // Prepare request data
        const requestData = {
            file_base64: base64Data,
            file_type: fileType,
            job_description: jobDescription.value.trim()
        };

        // Call API
        const response = await fetch('http://localhost:8001/api/analyze-resume', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const result = await response.json();

        // Display results
        loading.style.display = 'none';
        resultsContent.style.display = 'block';
        displayResults(result);

    } catch (error) {
        loading.style.display = 'none';
        resultsContent.style.display = 'block';
        resultsContent.innerHTML = `
            <div class="error">
                <strong>Error:</strong> ${error.message}
                <br><br>
                <small>Make sure the backend server is running on http://localhost:8001</small>
            </div>
        `;
    }
});

// Helper: Convert file to base64
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => {
            // Remove the data:*/*;base64, prefix
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = error => reject(error);
    });
}

// Helper: Get file extension
function getFileExtension(filename) {
    return filename.split('.').pop().toLowerCase();
}

// Helper: Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Helper: Display results
function displayResults(result) {
    let html = '';

    if (result.error) {
        html = `<div class="error">${result.error}</div>`;
    } else {
        // Format the response text with basic markdown-like parsing
        const text = result.response || 'No response received';
        
        // Convert markdown-style formatting to HTML
        html = text
            .replace(/## (.*?)$/gm, '<h3>$1</h3>')
            .replace(/### (.*?)$/gm, '<h4>$1</h4>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/- (.*?)$/gm, '<li>$1</li>')
            .replace(/```([\s\S]*?)```/g, '<pre>$1</pre>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        
        html = `<div>${html}</div>`;
    }

    resultsContent.innerHTML = html;
}
