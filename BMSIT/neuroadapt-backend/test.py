from pathlib import Path
import fitz  # PyMuPDF

pdf_path = r"C:\Users\H K Puneet\Downloads\lol.pdf"

doc = fitz.open(pdf_path)
text = doc[0].get_text()

print(f"Page 1 has {len(text)} chars")
print(f"First 200 chars: {text[:200]}")

doc.close()
