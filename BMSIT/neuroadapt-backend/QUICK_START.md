# NeuroAdapt Backend - Quick Start

## 🚀 Get Started in 5 Minutes

### Step 1: Navigate to Backend Directory
```bash
cd "Desktop/New folder/neuroadapt-backend"
```

### Step 2: Run Setup Script

**On Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

**On Windows:**
```cmd
setup.bat
```

This will:
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Create `.env` configuration
- ✅ Create `models/` directory

### Step 3: Install & Start Ollama

**Download & Install Ollama:**
- https://ollama.ai (1-click installer for Windows/macOS)
- Or: `curl https://ollama.ai/install.sh | sh` (Linux)

**Start Ollama in a separate terminal:**
```bash
ollama run qwen2.5:1.5b
```

This downloads the model (~1.5GB) and starts the server. **Keep this terminal open.**

You should see:
```
pulling manifest
pulling 1avf5e5c65db
pulling 1e9566efeb79
pulling 8f6e5d2f5d6f
verifying sha256 digest
...
listening on 127.0.0.1:11434
```

Now backend can access the model via `http://localhost:11434`

### Step 4: Start Backend Server

**Important:** Ollama must be running in a separate terminal first!

```bash
# Terminal 2 (Backend)
python -m uvicorn main:app --reload
```

Output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
[STARTUP] NeuroAdapt Backend starting...
[AGENT:simplify] Using Ollama model: qwen2.5:1.5b
```

**You should now have 2 terminals running:**
- Terminal 1: `ollama run qwen2.5:1.5b` (port 11434)
- Terminal 2: `python -m uvicorn main:app --reload` (port 8000)

### Step 5: Test API

Open browser or use curl:
```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "ok"}
```

View API docs: **http://localhost:8000/docs**

---

## 📤 Upload a PDF

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@chapter.pdf"
```

Save the `job_id` from response:
```json
{"job_id": "abc-123-def-456", "status": "processing"}
```

---

## 📊 Check Status

```bash
JOB_ID="abc-123-def-456"

curl "http://localhost:8000/status/$JOB_ID"
```

Response:
```json
{
  "job_id": "abc-123-def-456",
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

---

## 📥 Get Result

When `status` changes to `"complete"`:

```bash
curl "http://localhost:8000/result/$JOB_ID" > result.json

# Extract HTML
jq -r '.html' result.json > output.html

# Open in browser
open output.html  # macOS
# xdg-open output.html  # Linux
# start output.html  # Windows
```

---

## 🔧 Configuration

Edit `.env` if needed:

```env
# Path to model file
LLAMA_MODEL_PATH=./models/qwen2.5-1.5b-instruct-q4_k_m.gguf

# Server port
PORT=8000

# Development mode
RELOAD=true
```

---

## ⚠️ Troubleshooting

### "Model not found"
- Check `.env` file has correct path
- Verify model file exists in `models/` directory
- Restart server after placing model

### "Out of memory"
- Use Q4 quantization (not Q5/Q8)
- Reduce paragraph size in `simplify_agent.py`

### "Tesseract not found" (for scanned PDFs)
- **Linux:** `sudo apt-get install tesseract-ocr`
- **macOS:** `brew install tesseract`
- **Windows:** Download from https://github.com/UB-Mannheim/tesseract/wiki

### CORS errors from frontend
- Backend already configured for `localhost:3000`
- Check frontend is on correct port
- Edit `main.py` line ~198 to add custom origins

---

## 📚 Full Documentation

See [README.md](./README.md) for:
- Complete API reference
- HTML output format
- Performance tuning
- Contribution guide
- Architecture details

---

## 🎯 Next Steps

1. **Frontend Connection:**
   - Ensure Next.js frontend running on `localhost:3000`
   - Backend automatically configured for CORS

2. **Test End-to-End:**
   - Upload NCERT chapter via frontend
   - Watch processing progress
   - View dyslexia-friendly output

3. **Production Deployment:**
   - See README.md "Integration with Frontend" section
   - Configure CORS for your domain
   - Use production ASGI server (Gunicorn + Uvicorn)

---

## 💡 Tips

- **First request slow?** Model is loading. Subsequent requests are fast.
- **Want better quality?** Download Q5 model instead of Q4 (slower but more accurate)
- **Need offline mode?** Backend runs completely offline after model download
- **Check logs?** Output shows agent progress in real-time

Happy transforming! 🧠✨
