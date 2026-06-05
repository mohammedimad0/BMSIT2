# OCR Extraction Debugging Guide

## What You're Seeing

The error "failed to extract text from source" means the OCR agent couldn't read text from your PDF/image using either:
1. **PyMuPDF** (primary method for digital PDFs)
2. **Tesseract** (fallback for scanned PDFs/images)

## Quick Diagnostic Checklist

### 1. Check File Format
```bash
# What kind of file are you uploading?
file your_file.pdf        # Linux/macOS
Get-Item .\your_file.pdf  # PowerShell (Windows)
```

**Expected output:**
- PDF: Shows `PDF document, version 1.4` or similar
- Image: Shows `PNG image` or `JPEG image` etc.

### 2. Check If File Has Text (Digital vs Scanned)

```bash
# Try this locally first
python

from pathlib import Path
import fitz  # PyMuPDF

doc = fitz.open("your_file.pdf")
text = doc[0].get_text()
print(f"Page 1 has {len(text)} chars")
print(f"First 200 chars: {text[:200]}")
doc.close()
```

- **Digital PDF**: Should print text content (> 100 chars)
- **Scanned PDF**: Will print empty or very little text (< 100 chars)

### 3. Verify Dependencies

Check what's installed:
```bash
python -c "import fitz; print(f'PyMuPDF: {fitz.__version__}')"
python -c "import pytesseract; print('Tesseract: OK')"
python -c "from pdf2image import convert_from_path; print('pdf2image: OK')"
python -c "from PIL import Image; print('Pillow: OK')"
```

### 4. Check Backend Logs

**Start backend with verbose logging:**
```bash
# Terminal 2 (Backend)
python -m uvicorn main:app --reload --log-level debug
```

**Look for these log messages when you upload a file:**
```
[API:upload] New job abc-123
[API:upload] File upload: your_file.pdf (size: 1234567 bytes)
[API:upload] Read 1234567 bytes from file
[AGENT:ocr] Starting (source_type=pdf, input_type=bytes)
[AGENT:ocr] Received 1234567 bytes
[AGENT:ocr] Trying PyMuPDF extraction...
[AGENT:ocr] Opened PDF with 10 pages
[AGENT:ocr] Page 1: 2000 chars
...
[AGENT:ocr] PyMuPDF complete: 10 pages, 20000 chars total
```

If PyMuPDF fails, you'll see:
```
[AGENT:ocr] PyMuPDF extraction failed: [specific error]
[AGENT:ocr] Text too short (< 100 chars), switching to Tesseract
[AGENT:ocr] Attempting Tesseract extraction...
```

### 5. Test Extraction Manually

Create a test script:
```bash
# test_ocr.py
import sys
from agents.ocr_agent import run
from models import PipelineState

# Test with your file
with open("your_file.pdf", "rb") as f:
    file_bytes = f.read()

state = PipelineState(job_id="test-123")
result = run(state, file_bytes, "pdf")

print(f"Success: {len(result.raw_text)} chars extracted")
print(f"Degraded: {result.degraded}")
print(f"Errors: {result.errors}")
print(f"First 500 chars: {result.raw_text[:500]}")
```

Run it:
```bash
python test_ocr.py
```

## Common Issues & Solutions

### Issue 1: "PyMuPDF extraction failed: cannot open display"
**Cause:** PyMuPDF trying to use GUI (rare)
**Solution:** Already handled - should fallback to Tesseract

### Issue 2: "pytesseract/pdf2image/PIL not installed"
**Cause:** Dependencies missing
**Solution:**
```bash
pip install pytesseract pdf2image Pillow
```

Then install Tesseract system package:

**Windows:**
- Download: https://github.com/UB-Mannheim/tesseract/wiki
- Install and add to PATH

**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr poppler-utils
```

### Issue 3: "No text extracted" but file is digital PDF
**Cause:** PDF might have unusual encoding or protection
**Solutions:**
1. Try opening PDF in Adobe - if it opens, it should work
2. Try converting PDF offline first:
   ```bash
   python
   import fitz
   doc = fitz.open("your_file.pdf")
   text = doc[0].get_text("text")  # Try "text" mode
   print(text[:500])
   ```

### Issue 4: File got corrupted in transit
**Cause:** Upload error or large file
**Solution:**
1. Try smaller file first (< 5MB)
2. Check file size in logs matches original
3. Use curl to test:
   ```bash
   curl -X POST "http://localhost:8000/upload" \
     -F "file=@test.pdf"
   ```

## Validating Your File Works

```bash
# Create a simple test PDF (if you have a PDF library)
python

from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.cell(200, 10, txt="This is a test PDF with text content.", ln=True)
pdf.output("test_simple.pdf")

# Now upload test_simple.pdf to backend
# Should work!
```

## Next Steps After Finding Issue

1. **If PyMuPDF is failing:**
   - Reinstall: `pip install --force-reinstall PyMuPDF`
   - Or use only Tesseract by modifying ocr_agent.py

2. **If Tesseract is failing:**
   - Install system package (see Issue 2)
   - Or install Tesseract via conda if using conda

3. **If you only have scanned PDFs:**
   - Tesseract is the right tool - ensure it's installed
   - May take longer (OCR is slow)

4. **To skip OCR entirely (if just testing):**
   - Use the direct text input endpoint:
     ```bash
     curl -X POST "http://localhost:8000/upload" \
       -H "Content-Type: application/json" \
       -d '{"text": "Your text content here..."}'
     ```

## Checking Full Pipeline Status

Once file uploads, check full processing:
```bash
curl "http://localhost:8000/status/your-job-id"
```

Look for:
```json
{
  "agent_statuses": {
    "ocr": "ok",        // ← Should be "ok" if extraction worked
    "preprocess": "...",
    "simplify": "...",
    "dyslexia": "...",
    "html": "..."
  },
  "degraded": false
}
```

If `"ocr": "failed"`, get details:
```bash
curl "http://localhost:8000/result/your-job-id"
```

Check `errors` array for exact failure message.

---

## Quick Start Test

Use a simple test without OCR:
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Photosynthesis is the process by which plants make food using sunlight. Chlorophyll is the green pigment that captures light energy. Mitochondria are the powerhouse of cells."
  }'
```

This skips OCR entirely and tests the rest of the pipeline. If this works, the issue is with OCR.

---

**Need more help?** Share your logs from the backend terminal and I can diagnose the exact issue! 🔍
