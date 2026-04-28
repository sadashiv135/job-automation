import os
import re
from pathlib import Path
import anthropic
from docx import Document
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
RESUMES_DIR = Path(__file__).parent / "resumes"
BASE_RESUME_PATH = Path(os.environ.get("RESUME_PATH", Path(__file__).parent / "resume.docx"))


def _read_docx(path: Path) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _safe_filename(text: str) -> str:
    return re.sub(r"[^\w\-]", "_", text.strip()).lower()


def _write_docx(content: str, path: Path) -> None:
    doc = Document()
    for line in content.split("\n"):
        doc.add_paragraph(line)
    doc.save(path)


def tailor_resume(job: dict) -> Path:
    """Tailor base resume to job description. Returns path to tailored .docx."""
    os.makedirs(RESUMES_DIR, exist_ok=True)
    base_text = _read_docx(BASE_RESUME_PATH)
    jd = job["description"]
    company = _safe_filename(job["company"])
    title = _safe_filename(job["title"])
    out_path = RESUMES_DIR / f"{company}_{title}_resume.docx"

    prompt = f"""You are a professional resume editor. Your task is to tailor the candidate's resume
to better match a specific job description — WITHOUT fabricating or inventing any experience,
projects, skills, or achievements that are not already present in the base resume.

RULES (strictly follow):
1. Keep all experience stories, project descriptions, and achievements exactly the same.
2. You MAY adjust or reorder skill/tech-stack keywords to mirror the JD language.
3. You MAY reword existing bullet points to use JD terminology where the underlying skill is the same.
4. You MAY rearrange the order of bullets within a section to surface the most relevant items first.
5. NEVER add a skill, tool, technology, or achievement that does not appear in the base resume.
6. NEVER remove critical experience sections.
7. Return ONLY the final resume text, preserving the same section structure.

BASE RESUME:
{base_text}

JOB DESCRIPTION:
{jd}

Output the tailored resume text below:"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    tailored_text = message.content[0].text
    _write_docx(tailored_text, out_path)
    print(f"[tailor] Saved tailored resume → {out_path.name}")
    return out_path
