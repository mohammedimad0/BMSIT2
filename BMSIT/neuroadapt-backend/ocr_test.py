#!/usr/bin/env python
"""
Quick OCR diagnostic script - test extraction without backend
"""

import sys
from pathlib import Path

def test_pymupdf():
    """Test PyMuPDF installation and basic functionality"""
    try:
        import fitz
        print("✅ PyMuPDF installed:", fitz.__version__)
        return True
    except ImportError as e:
        print("❌ PyMuPDF not installed:", str(e))
        return False

def test_tesseract():
    """Test Tesseract installation"""
    try:
        import pytesseract
        print("✅ pytesseract installed")
        
        # Try to call tesseract
        try:
            result = pytesseract.get_tesseract_version()
            print(f"✅ Tesseract command available: {result}")
            return True
        except Exception as e:
            print(f"❌ Tesseract command not found: {str(e)}")
            print("   Install with:")
            print("   - Windows: https://github.com/UB-Mannheim/tesseract/wiki")
            print("   - macOS: brew install tesseract")
            print("   - Linux: sudo apt-get install tesseract-ocr")
            return False
    except ImportError as e:
        print("❌ pytesseract not installed:", str(e))
        return False

def test_pdf_conversion():
    """Test PDF to image conversion"""
    try:
        from pdf2image import convert_from_path
        from PIL import Image
        print("✅ pdf2image and PIL installed")
        return True
    except ImportError as e:
        print("❌ pdf2image or PIL not installed:", str(e))
        return False

def test_file_extraction(file_path: str):
    """Test extracting text from a real file"""
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"\n📄 Testing file: {file_path}")
    print(f"   Size: {file_path.stat().st_size} bytes")
    print(f"   Type: {file_path.suffix}")
    
    # Test with PyMuPDF
    try:
        import fitz
        doc = fitz.open(str(file_path))
        print(f"✅ PyMuPDF opened file: {len(doc)} pages")
        
        # Try first page
        text = doc[0].get_text()
        print(f"   Page 1 extracted: {len(text)} chars")
        if len(text) > 0:
            print(f"   First 150 chars: {text[:150]}")
        else:
            print("   ⚠️  Page 1 has no text (might be scanned PDF)")
        
        doc.close()
    except Exception as e:
        print(f"❌ PyMuPDF failed: {str(e)}")
    
    # Test with Tesseract if PDF
    if file_path.suffix.lower() == '.pdf':
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            print("✅ Trying Tesseract OCR...")
            images = convert_from_path(str(file_path), dpi=300, first_page=1, last_page=1)
            
            if images:
                text = pytesseract.image_to_string(images[0])
                print(f"   Tesseract extracted: {len(text)} chars")
                if len(text) > 0:
                    print(f"   First 150 chars: {text[:150]}")
                else:
                    print("   ⚠️  Tesseract found no text (blank page?)")
            
        except Exception as e:
            print(f"❌ Tesseract failed: {str(e)}")

def main():
    print("=" * 60)
    print("NeuroAdapt - OCR Diagnostic Tool")
    print("=" * 60)
    
    print("\n📦 Checking dependencies...")
    pymupdf_ok = test_pymupdf()
    tesseract_ok = test_tesseract()
    pdf_tools_ok = test_pdf_conversion()
    
    print("\n" + "=" * 60)
    
    if not (pymupdf_ok and tesseract_ok and pdf_tools_ok):
        print("⚠️  Some dependencies are missing!")
        print("\nTo fix, run:")
        print("  pip install -r requirements.txt")
        print("  pip install --force-reinstall PyMuPDF pytesseract pdf2image Pillow")
        return
    
    print("✅ All dependencies installed!")
    
    # Test with a file if provided
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        test_file_extraction(file_path)
    else:
        print("\n💡 Usage:")
        print("  python ocr_test.py <path_to_pdf_or_image>")
        print("\nExample:")
        print("  python ocr_test.py test.pdf")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
