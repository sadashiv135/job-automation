import os
from pathlib import Path
import anthropic
from docx import Document
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
BASE_RESUME_PATH = Path(__file__).parent / "resume.docx"


def _read_docx(path: Path) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def score_match(job: dict) -> tuple[int, str]:
    """Score resume–JD match. Returns (score_percent, reason_string)."""
    base_text = _read_docx(BASE_RESUME_PATH)
    jd        = job["description"]

    prompt = f"""You are a senior technical recruiter and ATS expert evaluating resume-to-job-description fit.

CANDIDATE PROFILE (use this as grounding context for your score):
- Total experience : 4 years (Software Engineer at Capgemini India + current Software Engineer Intern at a US healthcare startup)
- Core stack       : Java, Spring Boot, Python, React, Vue, TypeScript, REST APIs, Microservices
- Cloud & Data     : AWS (Lambda, S3, CloudWatch), Snowflake, DynamoDB, PostgreSQL
- Education        : MS Information Technology, UT Dallas — graduating May 2026
- Visa status      : F-1 OPT authorised from May 24 2026; STEM OPT extension eligible (3-year total work authorisation)
- Target roles     : Software Engineer, Full Stack Engineer, Backend Engineer, Data Engineer
- Seniority target : Mid-level (aligns with "2–5 years" job requirements)

SCORING CRITERIA:
1. Required technical skills coverage (40 pts)
   - Award full credit when the candidate's stack is equivalent (e.g. Vue ≈ React for UI roles; Spring Boot ≈ Express for API roles)
   - Deduct only for PRIMARY hard-required skills that are genuinely absent
2. Experience & seniority alignment (30 pts)
   - 4 years aligns well with "mid-level", "2–4 years", "3–5 years" requirements — award full credit
   - Do NOT penalise for lack of senior/staff-level experience on mid-level roles
3. Project & domain relevance (20 pts)
   - Healthcare SaaS, enterprise software, cloud-native, data pipelines all count as relevant
4. Education & credentials (10 pts)
   - MS from a US university (UT Dallas) is a strong positive signal

ADDITIONAL NOTES:
- OPT work authorisation is NOT a liability — candidate is fully work-authorised from May 2026
- "No sponsorship available" clauses are acceptable (candidate does not need H1B sponsorship during OPT)
- Score 70+ when the candidate meets ≥70% of stated required skills
- Be realistic but not overly conservative — small skill gaps that can be closed quickly should not tank the score

RESUME:
{base_text}

JOB DESCRIPTION:
{jd}

Respond in EXACTLY this format (no extra text):
SCORE: <integer 0-100>
REASON: <2-3 sentences explaining the match: key strengths, any real gaps, and overall fit>"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    raw    = message.content[0].text.strip()
    score  = 0
    reason = raw

    for line in raw.splitlines():
        if line.startswith("SCORE:"):
            try:
                score = int(line.split(":", 1)[1].strip())
            except ValueError:
                score = 0
        elif line.startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()

    print(f"[scorer] {score}% — {reason[:90]}...")
    return score, reason
