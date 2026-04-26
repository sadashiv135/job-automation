"""
launcher.py — portal detection utility.

Browser auto-opening has been removed. The pipeline now saves everything
to jobs.xlsx silently. Open that file to review and apply manually.
"""

PORTAL_DOMAINS: dict[str, str] = {
    "myworkdayjobs.com": "Workday",
    "greenhouse.io":     "Greenhouse",
    "lever.co":          "Lever",
    "ashbyhq.com":       "Ashby",
    "smartrecruiters.com": "SmartRecruiters",
    "jobvite.com":       "Jobvite",
    "taleo.net":         "Taleo",
    "icims.com":         "iCIMS",
    "breezy.hr":         "Breezy",
}


def detect_portal(url: str) -> str:
    """Return the ATS/portal name for a given URL, or 'LinkedIn' / 'Job Board'."""
    if not url or url == "N/A":
        return "N/A"
    if "linkedin.com" in url:
        return "LinkedIn"
    for domain, name in PORTAL_DOMAINS.items():
        if domain in url:
            return name
    return "Job Board"
