#!/usr/bin/env python3
"""Download + extract text from a single arXiv PDF using PyMuPDF."""

import sys, os, urllib.request, json, textwrap

URL = sys.argv[1]
out_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp/pdf_extracts"
os.makedirs(out_dir, exist_ok=True)

# Derive filename from URL
slug = URL.strip("/").split("/")[-1].replace(".pdf", "")
out_path = os.path.join(out_dir, f"{slug}.txt")

# Download if not cached
pdf_path = os.path.join(out_dir, f"{slug}.pdf")
if not os.path.exists(pdf_path):
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=120).read()
        with open(pdf_path, "wb") as f:
            f.write(data)
    except Exception as e:
        print(f"DOWNLOAD ERROR: {e}")
        sys.exit(1)

# Extract text with PyMuPDF
import fitz
doc = fitz.open(pdf_path)
text_parts = []
for i, page in enumerate(doc):
    txt = page.get_text()
    if txt and txt.strip():
        text_parts.append(f"--- PAGE {i+1} ---\n{txt}")

full_text = "\n".join(text_parts)
if not full_text.strip():
    full_text = "[NO TEXT EXTRACTED - scanned or image-only PDF]"

with open(out_path, "w") as f:
    f.write(full_text)

# Print summary
word_count = len(full_text.split())
line_count = full_text.count("\n")
meta = {
    "url": URL,
    "slug": slug,
    "pages": len(doc),
    "words": word_count,
    "lines": line_count,
    "title_preview": text_parts[0].split("\n")[1:8] if text_parts else ["No text found"],
}
print(json.dumps(meta))
doc.close()
