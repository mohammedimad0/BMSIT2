# NeuroAdapt Backend

FastAPI server that transforms NCERT PDF chapters into dyslexia-friendly HTML. Runs fully offline on a teacher's machine.

## Architecture

**5-Agent Sequential Pipeline** (with independent fallbacks):

1. **OCR Agent** - Extract text from PDF/image
   - Primary: PyMuPDF (fitz) for digital PDFs
   - Fallback: Tesseract OCR for scanned PDFs

2. **Preprocess Agent** - Structure text into blocks
   - Detect headings, lists, paragraphs
   - Fix hyphenation breaks
   - Return semantic blocks

3. **Simplify Agent** - Reduce text complexity
   - Load Qwen2.5-1.5B-Instruct via llama-cpp-python
   - Simplify paragraphs keeping subject terms
   - Max 12 words per sentence, active voice only

4. **Dyslexia Agent** - Apply 4 independent transforms
   - A: Syllable splitting (pyphen)
   - B: Numbers to words (num2words)
   - C: Concept chunking (2-4 sentence groups)
   - D: Glossary injection (NCERT terms)

5. **HTML Agent** - Build semantic HTML
   - Chunk divs with data-hidden for progressive reveal
   - Sentence paragraphs with class="na-sentence"
   - Syllable data, glossary popups
   - Debug info in data attributes

**Key Features:**
- ✅ Every agent has independent fallback (pipeline **never crashes**)
- ✅ Single `PipelineState` object flows through all agents
- ✅ Model preloading at startup for fast first request
- ✅ In-memory job storage (no database)
- ✅ 1-hour job expiry with background cleanup
- ✅ CORS enabled for localhost:3000 (Next.js frontend)
- ✅ Complete diagnostic info on every request


## Installation

### 1. Clone & Setup

```bash
cd neuroadapt-backend
cp .env.example .env

# Create models directory
mkdir -p models
```

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 3. Install & Start Ollama

Ollama is a simple local LLM server that runs on port 11434.

**Download & Install:**
- Windows/macOS: https://ollama.ai (1-click installer)
- Linux: `curl https://ollama.ai/install.sh | sh`

**Start Ollama with Qwen2.5:**
```bash
ollama run qwen2.5:1.5b
```

This downloads the model (~1.5GB) and starts the server on `localhost:11434`. Leave this running in a separate terminal while NeuroAdapt is active.

**That's it!** No complex setup, no GGUF files to manage.

### 4. System Dependencies (Optional - for OCR)

For Tesseract OCR fallback (scanned PDFs):

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr libsm6 libxext6
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

### 5. Run Server

```bash
# Development (with reload)
RELOAD=true python -m uvicorn main:app --reload

# Production
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Server runs at `http://localhost:8000`

API docs: `http://localhost:8000/docs`


## API Endpoints

### 1. Upload & Process

**POST** `/upload`

Submit a file (PDF/image) or direct text for processing.

**File Upload:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@chapter.pdf"
```

**Direct Text:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Photosynthesis is the process by which plants make food using sunlight. Chlorophyll is the green pigment that captures light."
  }'
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-4g7h-8i9j...",
  "status": "processing"
}
```


### 2. Check Status

**GET** `/status/{job_id}`

Poll for processing progress.

```bash
curl "http://localhost:8000/status/a1b2c3d4-e5f6-4g7h-8i9j"
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-4g7h-8i9j",
  "status": "processing",
  "degraded": false,
  "agent_statuses": {
    "ocr": "ok",
    "preprocess": "ok",
    "simplify": "processing",
    "dyslexia": "not_started",
    "html": "not_started"
  }
}
```

Statuses: `"processing"`, `"complete"`, `"failed"`

Degraded: `true` if any agent hit fallback


### 3. Get Result

**GET** `/result/{job_id}`

Retrieve final HTML when complete.

```bash
curl "http://localhost:8000/result/a1b2c3d4-e5f6-4g7h-8i9j"
```

**Response (complete):**
```json
{
  "job_id": "a1b2c3d4-e5f6-4g7h-8i9j",
  "html": "<div class=\"na-document\" data-job-id=\"...\" data-degraded=\"false\">...",
  "degraded": false,
  "errors": [],
  "agent_statuses": {
    "ocr": "ok",
    "preprocess": "ok",
    "simplify": "ok",
    "dyslexia": "ok",
    "html": "ok"
  }
}
```

**Response (still processing - 202 Accepted):**
```json
{
  "status": "processing",
  "job_id": "a1b2c3d4-e5f6-4g7h-8i9j"
}
```


### 4. Delete Job

**DELETE** `/job/{job_id}`

Clean up stored result.

```bash
curl -X DELETE "http://localhost:8000/job/a1b2c3d4-e5f6-4g7h-8i9j"
```

**Response:**
```json
{
  "status": "deleted",
  "job_id": "a1b2c3d4-e5f6-4g7h-8i9j"
}
```


### 5. Health Check

**GET** `/health`

```bash
curl "http://localhost:8000/health"
```


## HTML Output Format

The HTML contains semantic structure for the Next.js frontend:

```html
<div class="na-document" data-job-id="..." data-degraded="false" data-agent-statuses='{"ocr":"ok",...}'>
  <!-- First chunk is visible by default -->
  <div class="na-chunk" data-chunk-id="1" data-hidden="false">
    <h2 class="na-heading">Chapter Title</h2>
  </div>
  
  <!-- Subsequent chunks hidden, revealed one at a time -->
  <div class="na-chunk" data-chunk-id="2" data-hidden="true">
    <p class="na-sentence">First sentence of simplified text.</p>
    <p class="na-sentence">Second sentence with <span class="na-word" data-syllables="pho·to·syn·the·sis">photosynthesis</span>.</p>
    <div class="na-glossary-popup" data-term="photosynthesis">how plants make food using sunlight</div>
  </div>
  ...
</div>
```

**Key Data Attributes:**
- `data-hidden`: "true" | "false" (controls visibility via JS)
- `data-chunk-id`: Numeric ID for tracking
- `data-syllables`: Syllable breaks for rendering (e.g., "pho·to·syn·the·sis")
- `data-term`: Glossary term for popup linking
- `data-degraded`: "true" if any agent used fallback
- `data-agent-statuses`: JSON of per-agent outcomes


## Configuration

### Environment Variables

Create `.env` from `.env.example`:

```env
# Ollama server endpoint (default: localhost:11434)
OLLAMA_BASE_URL=http://localhost:11434

# Ollama model to use (qwen2.5:1.5b is fast, qwen:110b is more accurate)
OLLAMA_MODEL=qwen2.5:1.5b

# Server port
PORT=8000

# Hot reload for development
RELOAD=true
```

### Ollama Configuration

Download additional models:
- **qwen2.5:1.5b** (~1.5GB, recommended) - Fast, good quality
- **qwen:110b** (~60GB, slow) - More accurate but needs GPU
- **qwen:7b** (~5GB) - Middle ground

To use a different model, just set `OLLAMA_MODEL` in `.env` and restart both Ollama and backend.

```bash
# Example: Use a larger model
OLLAMA_MODEL=qwen:7b
```

### CORS Configuration

Default allows:
- `http://localhost:3000` (Next.js dev)
- `http://localhost:3001` (alternate)

Edit `main.py` to allow additional origins in production.


## Performance

**Target:** 10-page NCERT chapter < 60 seconds on 8GB RAM, no GPU

**Typical timing (with Ollama qwen2.5:1.5b):**
- OCR (PyMuPDF): 1-3s
- Preprocess: 0.5-1s
- Simplify (Ollama qwen2.5): 25-35s
- Dyslexia transforms: 2-5s
- HTML build: 0.5-1s

**Total: ~30-45 seconds typical**

**Performance Tips:**
- Use `qwen2.5:1.5b` for fastest inference (~1.5GB VRAM)
- Use `qwen:7b` for better quality if you have 8GB+ VRAM
- Keep Ollama running in background (startup cost is small)
- First request loads model in memory, subsequent requests are cached


## Troubleshooting

### Model Load Fails
```
[AGENT:simplify] Ollama not available at http://localhost:11434
```
→ Ensure Ollama is running: `ollama run qwen2.5:1.5b` in a separate terminal

### Model Takes Too Long
→ First request loads model into memory. Subsequent requests are cached and much faster.

### "Connection refused" on Ollama port
→ Start Ollama: `ollama run qwen2.5:1.5b`
→ Check it's on localhost:11434: `curl http://localhost:11434/api/tags`

### Want Slower but Higher Quality
→ Edit `.env`: `OLLAMA_MODEL=qwen:7b` or `qwen:110b`
→ Restart Ollama: `ollama run qwen:7b`
→ Restart backend


## File Structure

```
neuroadapt-backend/
├── main.py              # FastAPI app & routes
├── pipeline.py          # Pipeline orchestrator
├── models.py            # Pydantic models
├── storage.py           # Job storage (in-memory)
├── requirements.txt     # Python dependencies
├── .env.example         # Configuration template
├── README.md            # This file
├── agents/
│   ├── __init__.py
│   ├── ocr_agent.py     # Extract text from PDF/image
│   ├── preprocess_agent.py  # Detect headings, lists, paragraphs
│   ├── simplify_agent.py    # Simplify via Ollama API
│   ├── dyslexia_agent.py    # Syllables, numbers, chunking, glossary
│   └── html_agent.py    # Build semantic HTML
└── models/              # (Empty - Ollama manages models)
    └── README.md        # Ollama setup instructions
```

**No need to manually download models!** Ollama handles everything via `ollama run qwen2.5:1.5b`


## Testing with curl

**Complete workflow:**

```bash
# 1. Upload PDF
JOB_ID=$(curl -s -X POST "http://localhost:8000/upload" \
  -F "file=@ncert_chapter.pdf" | jq -r '.job_id')

echo "Job ID: $JOB_ID"

# 2. Poll status every 5 seconds
while true; do
  STATUS=$(curl -s "http://localhost:8000/status/$JOB_ID" | jq -r '.status')
  DEGRADED=$(curl -s "http://localhost:8000/status/$JOB_ID" | jq -r '.degraded')
  
  echo "[$(date)] Status: $STATUS (degraded=$DEGRADED)"
  
  if [ "$STATUS" = "complete" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  sleep 5
done

# 3. Get result
curl -s "http://localhost:8000/result/$JOB_ID" | jq '.' > result.json

# 4. Extract HTML
jq -r '.html' result.json > output.html

# 5. Open in browser
open output.html  # macOS
# xdg-open output.html  # Linux
# start output.html  # Windows

# 6. Clean up
curl -X DELETE "http://localhost:8000/job/$JOB_ID"
```


## Integration with Frontend

The Next.js frontend ([frontend repo](../../)) consumes these endpoints:

1. Upload file → `POST /upload`
2. Poll status → `GET /status/{job_id}`
3. Fetch result → `GET /result/{job_id}`
4. Parse HTML → Render chunks progressively

Frontend talks to backend on `http://localhost:8000` (configurable via `NEXT_PUBLIC_BACKEND_URL`).


## Contributing

All agents are isolated (no inter-agent imports). To add a new transform:

1. Create `agents/new_agent.py` with `run(state: PipelineState) -> PipelineState` function
2. Add to pipeline in `pipeline.py`
3. Log via `logger.info(f"[AGENT:name] message")`
4. Catch ALL exceptions, never re-raise


## License

MIT License - NeuroAdapt Project
