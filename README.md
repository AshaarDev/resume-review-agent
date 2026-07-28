# Resume Review Agent

A FastAPI and React resume reviewer with three independent analysis branches:

- GPT-4o mini content feedback
- Gemini 3.6 Flash visual review
- Deterministic PDF layout measurements

The unified API returns partial results when one AI provider is unavailable. A
Gemini timeout or missing key, for example, does not discard a successful text
review or layout analysis.

The application also exposes a LangGraph workflow layer. It routes review
requests through a Resume Review Agent, preserves the three raw review
branches, uses GPT-5.6 Luna to synthesize their findings, and falls back to a
deterministic summary when synthesis is unavailable. Create and revise intents
are reserved for the future Resume Creator Agent.

## Resume quality policy

`backend/policies/resume-review-policy-v1.json` is the single source of truth
for the standards shared by the workflow:

- Achievement bullets follow the XYZ method semantically: accomplishment,
  meaningful measurement, and method.
- At least 60% of eligible achievement bullets should be meaningfully
  quantified.
- Candidates below five years of relevant experience should use no more than
  one nonblank content page; candidates at or above five years may use two.
- Important achievement metrics should be emphasized selectively in bold.

The policy is validated as Pydantic data, given an ID and version, and routed
to the appropriate review branch. GPT performs the content and experience
analysis, Gemini checks visible metric emphasis, and the Review Agent applies
the configured thresholds deterministically. The workflow response includes
the policy ID, version, and a finding for each rule. A future Resume Creator
Agent can consume the same findings and policy without copying prompt text or
redefining standards.

## Setup

Create and activate a virtual environment, then install the backend packages:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

Copy the example environment file:

```powershell
Copy-Item backend\.env.example backend\.env
```

Configure at least:

```env
OPENAI_API_KEY=your_openai_api_key_here
MODEL_NAME=gpt-4o-mini
ORCHESTRATOR_MODEL=gpt-5.6-luna
ORCHESTRATOR_REASONING_EFFORT=low
ORCHESTRATOR_TIMEOUT_SECONDS=60
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_VISION_MODEL=gemini-3.6-flash
GEMINI_TIMEOUT_SECONDS=60
```

`GEMINI_VISION_MODEL` is configurable, but the production default is the
account-verified `gemini-3.6-flash` model. `MODEL_NAME` remains the content
review model; `ORCHESTRATOR_MODEL` is used only for final synthesis.

## Document conversion

PDF rendering and layout analysis use PyMuPDF.

DOCX visual review requires one of:

- Windows development: Microsoft Word and `docx2pdf`
- Server deployments: LibreOffice (`libreoffice --headless`)

The processor detects an available converter. Text review can still succeed if
DOCX visual conversion is unavailable.

## Safety limits

These settings are checked before rendered pages are sent to Gemini:

```env
MAX_RESUME_FILE_BYTES=10485760
MAX_RESUME_PAGES=5
MAX_VISION_IMAGE_PIXELS=16000000
MAX_VISION_IMAGE_DIMENSION=4096
DOCUMENT_RENDER_DPI=144
DOCX_CONVERSION_TIMEOUT_SECONDS=60
MCP_ALLOWED_FILE_ROOTS=uploads
```

Each request receives a unique directory under `backend/temp/`. The API owns
that workspace through text extraction, conversion, rendering, layout
analysis, and visual review, then removes it in a `finally` block.

## Run the application

```powershell
Set-Location backend
..\venv\Scripts\uvicorn.exe main:app --reload --port 8001
```

Open <http://localhost:8001>. Interactive API documentation is available at
<http://localhost:8001/docs>.

## API

### `POST /api/analyze-resume`

Accepts:

```json
{
  "file_base64": "base64 document data",
  "file_type": "pdf",
  "job_description": "Optional job description"
}
```

Returns:

```json
{
  "content_review": {
    "status": "available",
    "response": "Content feedback",
    "error_code": null,
    "error_message": null
  },
  "visual_review": {
    "status": "available",
    "result": {
      "visual_score": 88,
      "pass_status": true,
      "strengths": ["Clear hierarchy"],
      "issues": [
        {
          "code": "INCONSISTENT_ALIGNMENT",
          "description": "Dates do not share a common edge.",
          "severity": "minor",
          "affected_area": "page 1",
          "recommendation": "Use one right-aligned date column."
        }
      ]
    },
    "error_code": null,
    "error_message": null,
    "page_count": 1
  },
  "layout_analysis": {
    "status": "available",
    "page_count": 1,
    "pages": []
  },
  "metadata": {
    "file_type": "pdf",
    "file_size_bytes": 12345,
    "page_count": 1,
    "processing_time_ms": 850.2
  }
}
```

An unavailable branch is explicit and never uses a fake score:

```json
{
  "status": "unavailable",
  "result": null,
  "error_code": "GEMINI_TIMEOUT",
  "error_message": "The visual review request timed out.",
  "page_count": 1
}
```

### `POST /api/analyze-resume-visual`

Runs only document preparation, deterministic layout analysis, and the Gemini
visual review. It is intended for visual-review testing and troubleshooting.

### `POST /api/resume-workflows`

Runs the LangGraph workflow:

```json
{
  "intent": "review",
  "file_base64": "base64 document data",
  "file_type": "pdf",
  "job_description": "Optional job description",
  "user_instructions": "Optional synthesis context"
}
```

The response includes workflow and agent statuses, the complete raw review,
normalized actions, structured synthesis, and a deterministic final message.
It never contains temporary paths, documents, images, or Base64.
It also includes `policy_id`, `policy_version`, and `review.policy_findings`,
which power the frontend Resume Standards scorecard.

`create` and `revise` are accepted without an upload and currently return
`not_implemented`; these routes are reserved for the future Resume Creator
Agent. The graph is compiled once at module load. No checkpointing is enabled
because workflow state currently refers to temporary request artifacts.

When Luna is unavailable or returns invalid structured output, the raw review
is preserved and deterministic synthesis is returned with an
`ORCHESTRATOR_MODEL_UNAVAILABLE` warning. Luna is skipped when all review
branches fail.

### Other endpoints

- `GET /api/health`
- `POST /api/chat`

## MCP review tools

Run the MCP server from the backend directory:

```powershell
Set-Location backend
..\venv\Scripts\python.exe mcp_server\resume_server.py
```

The review server exposes:

- `parse_resume` — extract text from a local resume
- `parse_resume_base64` — extract text from base64 input
- `review_resume` — GPT content review for supplied text
- `analyze_resume_from_file` — legacy text-only file review
- `analyze_resume_layout` — deterministic layout review from a local file
- `analyze_resume_layout_base64` — deterministic layout review from base64
- `review_resume_visual` — Gemini visual review from a local file
- `review_resume_visual_base64` — Gemini visual review from base64
- `review_resume_unified` — content, visual, and layout review from a file
- `review_resume_unified_base64` — unified review from base64
- `run_resume_review_workflow` — workflow review from an approved local file
- `run_resume_review_workflow_base64` — workflow review from Base64
- `get_resume_statistics` — basic text statistics

The layout, visual, and unified tools call the same orchestration service as
the FastAPI endpoints. They therefore share file and page limits, isolated
temporary workspaces, schema validation, stable issue codes, and partial
failure behavior. File-path tools are appropriate when the MCP client and
server share a filesystem; base64 variants support remote clients.

All path-based MCP tools resolve the submitted path and accept it only when it is
inside one of the comma-separated `MCP_ALLOWED_FILE_ROOTS`. Relative roots are
resolved from `backend/`; the default is `backend/uploads/`.
Parent-directory traversal and resolved paths outside these roots are rejected.
Add another upload or temporary directory only when it is explicitly intended
to hold MCP-accessible resumes. The internal `backend/temp/` workspace is not
client-accessible by default.

Base64 is accepted only as tool input. Visual and unified tool responses
contain structured review findings and page metadata, not rendered images or
image Base64.

The same canonical policy is exposed read-only as the MCP resource
`resume-policy://current`. This resource is a view of the backend policy, not a
second copy. MCP clients and the future Creator Agent can inspect the exact
version used by the review workflow.

## Tests

```powershell
.\venv\Scripts\python.exe -m pytest backend\tests -q
```

The suite covers workspace cleanup, upload and page limits, PDF rendering,
layout metrics, Google GenAI structured-response validation, timeout handling,
visual-review orchestration, unified partial results, the visual-only API, and
MCP tool/resource registration and structured results. Policy tests cover
model-specific prompt injection, XYZ and quantification coverage, experience
page tiers, blank-page exclusion, visible metric emphasis, and explicit
unavailable findings. Workflow tests mock external
providers and cover routing, synthesis fallback, deterministic layout actions,
workspace isolation, path security, and response leakage.

An optional real-provider smoke test is skipped unless explicitly enabled:

```powershell
$env:RUN_MANUAL_TESTS="1"
.\venv\Scripts\python.exe -m pytest backend\tests\manual_smoke_test.py -v -s
```

## Structure

```text
backend/
  agents/
    resume_review_agent.py
  core/
    config.py
    models.py
    policy_schemas.py
    review_schemas.py
    workflow_schemas.py
  policies/
    resume-review-policy-v1.json
  data/reference/
    text/good/
    text/bad/
    visual/good/
    visual/bad/
  routes/api.py
  services/
    document_processor.py
    gemini_service.py
    layout_analyzer.py
    message_formatter.py
    openai_service.py
    orchestrator_service.py
    policy_evaluator.py
    policy_prompt_builder.py
    review_pipeline.py
    resume_policy.py
    resume_parser.py
    visual_reviewer.py
  workflows/
    nodes/
      finalization_nodes.py
      review_nodes.py
    resume_workflow.py
    routing.py
    state.py
  tests/
  temp/                  # runtime only; ignored by Git
  uploads/               # approved staging area for path-based MCP tools
frontend/
  frontend-app/          # React client
  app.js                 # static client served by FastAPI
```
