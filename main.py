"""
AI Job Application Automation Pipeline
Run: python main.py
"""

import re
import sys
from pathlib import Path

from scraper import fetch_all_jobs, get_visa_status
from tailor import tailor_resume
from cover_letter import generate_cover_letter
from scorer import score_match
from logger import log_job
from google_sheets import log_job_to_sheets

BASE_RESUME = Path(__file__).parent / "resume.docx"

# ── Configuration ──────────────────────────────────────────────────────────────
MIN_MATCH_SCORE     = 60   # jobs below this are logged but not tailored
MAX_JOBS_TO_PROCESS = 200  # safety cap (50 per URL × 4 URLs)

# Seniority words that disqualify a role — matched as whole words in the job title
_SENIOR_PATTERN = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|manager|director|architect)\b",
    re.IGNORECASE,
)


def _is_senior_role(title: str) -> bool:
    return bool(_SENIOR_PATTERN.search(title))


def check_prerequisites() -> bool:
    if not BASE_RESUME.exists():
        print(
            "[main] ERROR: resume.docx not found.\n"
            f"       Expected: {BASE_RESUME}"
        )
        return False
    return True


def _print_summary(stats: dict) -> None:
    passed = stats["total"] - stats["seniority_filtered"] - stats["visa_filtered"]
    div    = "=" * 50
    print(f"\n{div}")
    print(f"  PIPELINE SUMMARY")
    print(div)
    print(f"  Total jobs scraped            : {stats['total']:>4}")
    print(f"  Pre-filtered (senior titles)  : {stats['seniority_filtered']:>4}")
    print(f"  Filtered (citizenship/clear)  : {stats['visa_filtered']:>4}")
    print(f"  Passed all filters            : {passed:>4}")
    print(f"  Scored >= {MIN_MATCH_SCORE}% (tailored)       : {stats['tailored']:>4}")
    print(f"  Skipped (low score)           : {stats['low_score']:>4}")
    if stats["errors"]:
        print(f"  Errors                        : {stats['errors']:>4}")
    print(div)
    print(f"  Results saved → Google Sheets (+ jobs.xlsx fallback)")
    print(f"{div}\n")


def _log(job, score, resume_path, cover_letter_path, status, reason=""):
    """Try Google Sheets first; fall back to jobs.xlsx on any error."""
    try:
        log_job_to_sheets(job, score, resume_path, cover_letter_path, status, reason)
    except Exception as e:
        print(f"  [sheets] WARN: {e} — falling back to jobs.xlsx")
        log_job(job, score, resume_path, cover_letter_path, status)


def process_job(job: dict, stats: dict) -> None:
    title   = job["title"]
    company = job["company"]

    # ── Pre-filter: seniority titles ───────────────────────────────────────────
    if _is_senior_role(title):
        stats["seniority_filtered"] += 1
        print(f"  [title] SKIP  {title} @ {company}")
        return  # Not logged — irrelevant role tier

    # ── Visa / citizenship filter ──────────────────────────────────────────────
    visa_status = get_visa_status(job.get("description", ""))
    job["visa_filter"] = visa_status

    if visa_status == "Skipped - Citizenship Required":
        stats["visa_filtered"] += 1
        _log(job, score=0, resume_path=None, cover_letter_path=None,
             status="Skipped (citizenship)", reason="")
        print(f"  [visa]  SKIP  {title} @ {company}")
        return

    # ── Match scoring ──────────────────────────────────────────────────────────
    score, reason = score_match(job)
    flag = " ★ OPT" if visa_status == "OPT Friendly" else ""
    print(f"  [score] {score:>3}%{flag}  {title} @ {company}")

    if score < MIN_MATCH_SCORE:
        stats["low_score"] += 1
        _log(job, score, resume_path=None, cover_letter_path=None,
             status="Skipped (low match)", reason=reason)
        return

    # ── Tailor + cover letter ──────────────────────────────────────────────────
    resume_path = tailor_resume(job)
    cl_path     = generate_cover_letter(job)
    _log(job, score, resume_path, cl_path, status="To Apply", reason=reason)
    stats["tailored"] += 1
    print(f"          → tailored: {resume_path.name}")


def main() -> None:
    print("=" * 50)
    print("  AI Job Application Automation")
    print("=" * 50)

    if not check_prerequisites():
        sys.exit(1)

    jobs = fetch_all_jobs()

    if not jobs:
        print("[main] No jobs found. Check APIFY_API_TOKEN or LinkedIn URLs.")
        sys.exit(0)

    jobs = jobs[:MAX_JOBS_TO_PROCESS]

    stats = {
        "total":               len(jobs),
        "seniority_filtered":  0,
        "visa_filtered":       0,
        "tailored":            0,
        "low_score":           0,
        "errors":              0,
    }

    print(f"\n[main] Processing {len(jobs)} job(s) — min match: {MIN_MATCH_SCORE}%\n")

    for job in jobs:
        try:
            process_job(job, stats)
        except Exception as e:
            print(f"  [ERROR] {job.get('title')} @ {job.get('company')}: {e}")
            stats["errors"] += 1

    _print_summary(stats)


if __name__ == "__main__":
    main()
