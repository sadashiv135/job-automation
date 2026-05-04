import os
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID    = "curious_coder/linkedin-jobs-scraper"

# LinkedIn search URLs — last 2 hours (f_TPR=r7200), Mid-Senior level (f_E=3), newest first
LINKEDIN_URLS = [
    "https://www.linkedin.com/jobs/search/?keywords=software%20engineer&location=United%20States&f_TPR=r10800&f_E=3&sortBy=DD",
    "https://www.linkedin.com/jobs/search/?keywords=full%20stack%20engineer&location=United%20States&f_TPR=r10800&f_E=3&sortBy=DD",
    "https://www.linkedin.com/jobs/search/?keywords=backend%20engineer&location=United%20States&f_TPR=r10800&f_E=3&sortBy=DD",
    "https://www.linkedin.com/jobs/search/?keywords=data%20engineer&location=United%20States&f_TPR=r10800&f_E=3&sortBy=DD",
]

# ── Visa filter phrases ────────────────────────────────────────────────────────

# Hard disqualifiers — OPT candidates cannot hold these roles
_CITIZENSHIP_PHRASES = [
    "us citizenship required",
    "u.s. citizenship required",
    "united states citizenship required",
    "must be a us citizen",
    "must be a u.s. citizen",
    "must be a united states citizen",
    "active security clearance",
    "ts/sci",
    "secret clearance",
    "top secret",
]

# Positive OPT signals — employer explicitly welcomes OPT/STEM OPT candidates
_OPT_FRIENDLY_PHRASES = [
    "stem opt",
    "opt extension",
    "opt friendly",
    "opt candidates",
    "opt students",
    "stem extension",
]


def get_visa_status(description: str) -> str:
    """Return one of: 'Skipped - Citizenship Required' | 'OPT Friendly' | 'OK'."""
    lower = description.lower()
    if any(phrase in lower for phrase in _CITIZENSHIP_PHRASES):
        return "Skipped - Citizenship Required"
    if any(phrase in lower for phrase in _OPT_FRIENDLY_PHRASES):
        return "OPT Friendly"
    return "OK"


def is_citizenship_required(description: str) -> bool:
    """Convenience wrapper — True when the role requires citizenship or clearance."""
    return get_visa_status(description) == "Skipped - Citizenship Required"


# ── Apify helpers ──────────────────────────────────────────────────────────────

def _run_actor(url: str) -> list[dict]:
    """Run the LinkedIn scraper actor for one search URL, hard-capped at 25 items."""
    client = ApifyClient(APIFY_TOKEN)
    run_input = {
        "urls": [url],
        "maxResults": 25,
    }
    label = url.split("keywords=")[1].split("&")[0].replace("%20", " ")
    print(f"[scraper] Starting Apify run → '{label}' ...")
    run = client.actor(ACTOR_ID).call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    items = items[:25]   # hard cap — actor sometimes ignores maxResults
    print(f"[scraper]   ✓ Run finished — {len(items)} items (capped at 25).")
    return items


def _map_item(item: dict) -> dict:
    """Map a raw Apify LinkedIn job item to the shared pipeline job format."""
    company     = item.get("companyName") or item.get("company") or "N/A"
    url         = item.get("applyUrl") or item.get("url") or item.get("jobUrl") or "N/A"
    salary      = item.get("salary") or item.get("salaryText") or "Not disclosed"
    description = (item.get("description") or item.get("descriptionText") or "").strip()
    posted_at   = item.get("postedAt") or item.get("publishedAt") or "N/A"
    exp_level   = item.get("experienceLevel") or "Mid-Senior Level"

    return {
        "id":               str(item.get("id") or item.get("jobId") or ""),
        "title":            item.get("title") or "N/A",
        "company":          company,
        "location":         item.get("location") or "N/A",
        "experience_level": exp_level,
        "salary":           salary,
        "url":              url,
        "apply_options":    [],
        "description":      description,
        "posted_at":        posted_at,
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_all_jobs() -> list[dict]:
    """Run actor for all 4 LinkedIn URLs, deduplicate, and return combined list."""
    seen_ids:  set[str]   = set()
    seen_keys: set[tuple] = set()
    combined:  list[dict] = []

    for url in LINKEDIN_URLS:
        raw_items = _run_actor(url)
        added = 0
        for item in raw_items:
            job    = _map_item(item)
            job_id = job["id"]
            key    = (job["title"].lower(), job["company"].lower())

            if (job_id and job_id in seen_ids) or key in seen_keys:
                continue
            if job_id:
                seen_ids.add(job_id)
            seen_keys.add(key)
            combined.append(job)
            added += 1

        print(f"[scraper]   {added} unique jobs kept after dedup.")

    combined.sort(key=lambda j: j.get("posted_at") or "", reverse=True)
    print(f"[scraper] Total unique jobs across all 4 queries: {len(combined)}")
    return combined
