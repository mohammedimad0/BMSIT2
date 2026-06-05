#!/bin/bash
# Quick setup script for NeuroAdapt Backend

set -e

echo "🧠 NeuroAdapt Backend Setup"
echo "============================"
echo ""

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+"
    exit 1
fi
echo "✅ Python $(python3 --version)"

# 2. Create venv
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "✅ Virtual environment activated"

# 3. Upgrade pip
echo "📤 Upgrading pip..."
pip install --upgrade pip setuptools wheel > /dev/null

# 4. Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt > /dev/null
echo "✅ Dependencies installed"

# 5. Create env file
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "✅ Created .env (edit MODEL path if needed)"
fi

# 5. Create models directory
# (No longer needed - Ollama manages models)

# 6. Check for Ollama
if command -v ollama &> /dev/null; then
    echo "✅ Ollama detected"
else
    echo ""
    echo "⚠️  Ollama not installed"
    echo ""
    echo "Download Ollama (one-click installer):"
    echo "  https://ollama.ai"
    echo ""
    echo "Or install via:"
    echo "  curl https://ollama.ai/install.sh | sh"
    echo ""
fi

echo ""
echo "🚀 Ready! Start services with:"
echo ""
echo "   Terminal 1 (Ollama):"
echo "      ollama run qwen2.5:1.5b"
echo ""
echo "   Terminal 2 (Backend):"
echo "      python -m uvicorn main:app --reload"
echo ""
echo "API docs: http://localhost:8000/docs"
echo ""
