# Using Ollama for Model Management

NeuroAdapt Backend uses **Ollama** to manage and run LLMs locally.

## Installation

**Option 1: Download Desktop App**
- Windows/macOS: https://ollama.ai
- Click to install, done!

**Option 2: Command Line**
```bash
curl https://ollama.ai/install.sh | sh
```

## Running the Model

Start Ollama with Qwen2.5 (recommended):
```bash
ollama run qwen2.5:1.5b
```

This automatically:
- Downloads the model (~1.5GB)
- Starts server on `localhost:11434`
- Keeps running until you stop it

**Keep this terminal open while backend is running.**

## Switching Models

Want different quality/speed tradeoff?

**Faster (but lower quality):**
```bash
ollama run qwen2.5:0.5b
```

**Higher quality (but slower):**
```bash
ollama run qwen:7b
```

**Much higher quality (very slow, needs GPU):**
```bash
ollama run qwen:110b
```

Edit `.env` to change `OLLAMA_MODEL` and restart both Ollama and backend.

## Checking Status

```bash
# List downloaded models
ollama list

# Test Ollama is running
curl http://localhost:11434/api/tags
```

## Freeing Disk Space

Models are stored in Ollama's directory:
- **Linux/macOS:** `~/.ollama/models`
- **Windows:** `%USERPROFILE%\.ollama\models`

Remove specific model:
```bash
ollama rm qwen:7b
```

## More Information

- Ollama: https://ollama.ai
- Available models: https://ollama.ai/library

