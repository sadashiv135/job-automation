"""
Run locally to encode resume.docx as base64 for the RESUME_DOCX_B64 GitHub Secret.

Usage:
    python encode_resume.py

Copy the printed string and paste it into:
    GitHub repo → Settings → Secrets and variables → Actions → New secret
    Name:  RESUME_DOCX_B64
    Value: <paste here>
"""

import base64
from pathlib import Path

resume = Path(__file__).parent / "resume.docx"

if not resume.exists():
    raise FileNotFoundError(f"resume.docx not found at {resume}")

encoded = base64.b64encode(resume.read_bytes()).decode("utf-8")

print("=" * 60)
print("Copy the string below and save it as the GitHub Secret")
print("RESUME_DOCX_B64")
print("=" * 60)
print(encoded)
print("=" * 60)
print(f"(encoded {resume.stat().st_size:,} bytes → {len(encoded):,} base64 chars)")
