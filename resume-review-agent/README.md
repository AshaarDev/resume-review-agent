# Resume Review Agent

A resume review assistant powered by OpenAI's GPT-4o-mini.

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

## Testing

### Option 1: Test Script (Quick Test)
Run the simple test script to verify the LLM connection:
```bash
cd backend
python test_agent.py
```

### Option 2: FastAPI Server (Full API Test)
Start the FastAPI server:
```bash
cd backend
uvicorn main:app --reload
```

Then test the API:
- **Health check:** http://localhost:8000/health
- **API docs:** http://localhost:8000/docs
- **Test chat endpoint:** Use the interactive docs or curl:
  ```bash
  curl -X POST "http://localhost:8000/api/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "Help me improve my resume"}'
  ```

## Project Structure

```
resume-review-agent/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── models.py            # Pydantic models
│   ├── openai_service.py    # OpenAI integration
│   ├── system_prompt.py     # Agent prompt
│   ├── test_agent.py        # Test script
│   ├── .env                 # Environment variables (not in git)
│   └── requirements.txt     # Python dependencies
└── frontend/                # React app (to be created)
```
