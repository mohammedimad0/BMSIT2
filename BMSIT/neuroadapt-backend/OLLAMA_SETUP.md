# Ollama Setup Guide for NeuroAdapt Backend

## Why Ollama?

Instead of dealing with complex `llama.cpp` installation, **Ollama** provides:
- ✅ One-click installer (Windows/macOS)
- ✅ Simple command-line setup (Linux)
- ✅ Automatic model downloads
- ✅ REST API on localhost:11434
- ✅ Zero configuration after install
- ✅ Works completely offline

---

## Installation (3 Steps)

### Step 1: Download & Install

**Windows & macOS:**
1. Go to https://ollama.ai
2. Click "Download"
3. Follow installer
4. Done!

**Linux:**
```bash
curl https://ollama.ai/install.sh | sh
```

**Verify installation:**
```bash
ollama --version
```

### Step 2: Start Ollama with Qwen Model

Open a terminal and run:
```bash
ollama run qwen2.5:1.5b
```

First time: downloads model (~1.5GB from HuggingFace). This takes 5-15 minutes depending on internet speed.

You should see:
```
pulling manifest
pulling 1avf5e5c65db
...
listening on 127.0.0.1:11434
```

**Leave this terminal open while backend is running.**

### Step 3: Verify Ollama is Working

In **another terminal**:
```bash
curl http://localhost:11434/api/tags
```

Should return JSON with model info. If you see output, Ollama is running!

---

## Running NeuroAdapt Backend

Now that Ollama is running:

```bash
# Terminal 2 (in neuroadapt-backend directory)
python -m uvicorn main:app --reload
```

You should see:
```
[STARTUP] Checking Ollama availability...
[STARTUP] Ollama available at http://localhost:11434
[AGENT:simplify] Using Ollama model: qwen2.5:1.5b
```

---

## Model Options

### Default: qwen2.5:1.5b (Recommended)
- **Size:** 1.5GB VRAM
- **Speed:** ~3-5 seconds per paragraph
- **Quality:** Good for simple simplification
- **Start:** `ollama run qwen2.5:1.5b`

### Faster: qwen2.5:0.5b
- **Size:** 500MB VRAM
- **Speed:** ~1-2 seconds per paragraph
- **Quality:** Basic (fewer features)
- **Start:** `ollama run qwen2.5:0.5b`

### Better: qwen:7b
- **Size:** 5GB VRAM
- **Speed:** ~10-15 seconds per paragraph
- **Quality:** Much better at understanding context
- **Start:** `ollama run qwen:7b`

### Best (Slow): qwen:110b
- **Size:** 60GB VRAM (GPU recommended)
- **Speed:** ~60+ seconds per paragraph
- **Quality:** State-of-the-art
- **Start:** `ollama run qwen:110b`

**To switch models:**
1. Stop Ollama (Ctrl+C)
2. Run: `ollama run qwen:7b` (or desired model)
3. Restart backend: `python -m uvicorn main:app --reload`
4. Edit `.env` to update `OLLAMA_MODEL=qwen:7b`

---

## Troubleshooting

### "ollama: command not found"
→ Ollama not installed or not in PATH
→ Download from https://ollama.ai and install

### "Cannot GET /api/tags" (in curl test)
→ Ollama not running
→ Check terminal with `ollama run qwen2.5:1.5b` is still open
→ Look for errors in that terminal

### Slow First Request
→ Normal! Model is loading into VRAM (~30-60 seconds)
→ Subsequent requests use cached model (much faster)

### Out of Memory Error
→ Switch to smaller model: `ollama run qwen2.5:0.5b`
→ Or close other apps to free RAM

### Model Download Slow
→ Internet speed dependent (1.5GB at ~5-10 Mbps = 2-5 minutes)
→ Can close and re-run `ollama run qwen2.5:1.5b` to resume

### "Model not found" in backend logs
→ Check Ollama is running with correct model
→ Run `ollama list` to see downloaded models
→ Check `.env` has correct `OLLAMA_MODEL` name

---

## Checking Status

### See Downloaded Models
```bash
ollama list
```

Output:
```
NAME                    ID              SIZE    MODIFIED
qwen2.5:1.5b           abcd1234        1.5GB   2 hours ago
qwen:7b                efgh5678        5.2GB   1 day ago
```

### Check Server is Running
```bash
curl http://localhost:11434/api/tags
```

### Monitor Model Loading
```bash
# In the Ollama terminal, you'll see:
# [Loading model...]
# [Done loading]
```

---

## Advanced: Custom Configuration

### Change Default Ollama Host

Edit `.env`:
```env
# Default is localhost:11434
OLLAMA_BASE_URL=http://192.168.1.100:11434
```

Then restart backend (useful for separate machine setup).

### Specify Model in Environment

Edit `.env`:
```env
# Use different model
OLLAMA_MODEL=qwen:7b
```

---

## GPU Acceleration (Optional)

If you have an NVIDIA GPU, Ollama automatically uses it if:
- NVIDIA CUDA toolkit is installed
- NVIDIA drivers are recent

Check GPU usage:
```bash
# Linux/macOS
nvidia-smi

# Windows
nvidia-smi.exe
```

If GPU is used, you'll see much faster inference (5-10x speedup).

---

## Multiple Models

You can have multiple models downloaded and switch between them:

```bash
# Download multiple models
ollama run qwen2.5:1.5b  # Leave running
ollama run qwen:7b       # Download in another terminal

# Switch in backend by editing .env
OLLAMA_MODEL=qwen:7b
```

Models are stored once on disk, so switching is instant (no re-download).

---

## Free Space

Models stored in:
- **Linux/macOS:** `~/.ollama/models`
- **Windows:** `%USERPROFILE%\.ollama\models`

Remove specific model:
```bash
ollama rm qwen2.5:1.5b
```

Remove all models:
```bash
ollama rm -all   # Not recommended unless needed
```

---

## Next Steps

1. ✅ Install Ollama
2. ✅ Run `ollama run qwen2.5:1.5b`
3. ✅ Start backend: `python -m uvicorn main:app --reload`
4. ✅ Upload PDF via API

See [QUICK_START.md](./QUICK_START.md) for API examples.

---

## More Info

- **Ollama Home:** https://ollama.ai
- **Model Library:** https://ollama.ai/library
- **GitHub:** https://github.com/jmorganca/ollama
- **Community:** https://discord.gg/ollama
