# Resume Review Agent

A resume review assistant powered by OpenAI's GPT-4o-mini with advanced parsing capabilities for PDF, DOCX, images, and text files.

## Setup

1. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   - Edit `backend/.env` and add your OpenAI API key:
     ```
     OPENAI_API_KEY=sk-your-actual-api-key-here
     ```

3. **Install system dependencies (for OCR):**
   - **Windows:** Download Tesseract from [here](https://github.com/UB-Mannheim/tesseract/wiki)
   - **macOS:** `brew install tesseract`
   - **Linux:** `sudo apt-get install tesseract-ocr`

## Features

### Resume Parsing
- **PDF Support:** Extract text from multi-page PDF resumes
- **DOCX Support:** Parse Word document resumes
- **Image OCR:** Extract text from scanned resumes or screenshots (JPG, PNG, GIF, BMP, TIFF)
- **Text Input:** Direct plain text resume input
- **Base64 Upload:** Support for API file uploads

### Analysis Capabilities
- Text extraction and word count
- Formatting detection (bullets, sections, headings)
- File metadata analysis
- Visual quality assessment

### MCP Tools
- `review_resume`: Parse and analyze resume with optional job description
- `create_resume`: Generate resume from structured data (coming soon)

## Testing

### Option 1: Test Resume Parser
Test the resume parsing functionality:
```bash
cd backend
python test_resume_parser.py
```

### Option 2: Test LLM Connection
Run the simple test script to verify the LLM connection:
```bash
cd backend
python test_agent.py
```

### Option 3: Test MCP Server
Test the MCP server with resume tools:
```bash
cd backend
python mcp/client/mcp_client.py
```

### Option 4: Frontend + Backend (Full Application)
Start the FastAPI server:
```bash
cd backend
uvicorn main:app --reload --port 8001
```

Then open the frontend:
- **Open:** http://localhost:8001
- **Upload a resume** (PDF, DOCX, or image)
- **Add job description** (optional)
- **Click "Analyze Resume"** to get AI feedback

### Option 5: API Testing
Test the API endpoints directly:
- **Health check:** http://localhost:8001/health
- **API docs:** http://localhost:8001/docs
- **Test chat endpoint:**
  ```bash
  curl -X POST "http://localhost:8000/api/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "Help me improve my resume"}'
  ```

## Project Structure

```
resume-review-agent/
├── backend/
│   ├── main.py                      # FastAPI server
│   ├── models.py                    # Pydantic models
│   ├── openai_service.py            # OpenAI integration
│   ├── system_prompt.py             # Agent prompt
│   ├── test_agent.py                # LLM test script
│   ├── test_resume_parser.py        # Parser test script
│   ├── mcp/
│   │   ├── servers/
│   │   │   ├── resume_server.py     # MCP server with tools
│   │   │   └── resume_parser.py     # Resume parsing utilities
│   │   └── client/
│   │       └── mcp_client.py        # MCP client
│   ├── .env                         # Environment variables (not in git)
│   └── requirements.txt             # Python dependencies
└── frontend/
    ├── index.html                   # Main HTML page
    ├── styles.css                   # Styling
    └── app.js                       # Frontend logic
```
