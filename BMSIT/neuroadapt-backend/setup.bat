@echo off
REM NeuroAdapt Backend Setup (Fixed)

echo 🧠 NeuroAdapt Backend Setup
echo ============================
echo.

REM 1. Python Check
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found!
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION%

REM 2. Virtual Environment (Inside project)
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo ✅ Virtual environment activated

REM 3. Pip & Dependencies
echo 📤 Upgrading pip...
python -m pip install --upgrade pip setuptools wheel >nul 2>&1

echo 📥 Installing dependencies...
pip install -r requirements.txt >nul 2>&1
echo ✅ Dependencies installed

REM 4. .env File
echo 📝 Setting up .env file...
if not exist ".env" (
    copy .env.example .env >nul
    echo ✅ Created .env from .env.example
) else (
    echo ✅ .env already exists
)

REM 5. Ollama Check
echo.
echo 🔍 Checking Ollama...
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Ollama is available
) else (
    echo ⚠️  Ollama not detected in PATH
    echo    Try restarting Command Prompt or add Ollama to PATH
)

echo.
echo 🚀 Setup Complete!
echo.
echo Next Steps:
echo   1. Terminal 1 → ollama run qwen2.5:1.5b
echo   2. Terminal 2 → python -m uvicorn main:app --reload
echo.
pause