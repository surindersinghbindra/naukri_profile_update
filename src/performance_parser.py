"""
Naukri.com Performance Analytics Parser.
Navigates to the Naukri performance page and extracts recruiter views,
downloads, NVites, top search keywords, and trending skills.
"""

import logging
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .config import Config
from .utils import human_delay

logger = logging.getLogger("naukri_updater")

PERFORMANCE_URL = (
    "https://www.naukri.com/mnjuser/performance"
    "?manageTrendSkills=true&utmTerm=360Pro_PaidUserPage&utmContent=PP_activity_skills"
)


def fetch_performance_metrics(page: Page, config: Config) -> dict:
    """
    Navigate to the performance page and extract key metrics.

    Returns dict containing:
      - overall_summary (str)
      - action_breakdown (list of str)
      - recent_activities (list of str)
      - top_keywords (list of str)
      - trending_skills (list of str)
    """
    logger.info("📊 Fetching performance & analytics metrics from Naukri...")

    result = {
        "overall_summary": "",
        "action_breakdown": [],
        "recent_activities": [],
        "top_keywords": [],
        "trending_skills": [],
    }

    try:
        page.goto(PERFORMANCE_URL, wait_until="domcontentloaded", timeout=25000)
        human_delay(3, 5)

        raw_text = page.locator("body").inner_text()
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

        # 1. Overall Summary (e.g. "47 recruiter actions in 90 days (37% less actions since last week)")
        summary_parts = []
        for line in lines:
            if "recruiter actions in" in line.lower():
                summary_parts.append(line)
            elif "less actions since" in line.lower() or "more actions since" in line.lower():
                summary_parts.append(f"({line})")
        result["overall_summary"] = " ".join(summary_parts)

        # 2. Action Breakdown
        valid_breakdowns = ["profile views", "contact view", "resume downloaded", "nvites", "profile bookmarks"]
        for line in lines:
            lower = line.lower()
            if any(lower.endswith(b) for b in valid_breakdowns):
                if line not in result["action_breakdown"] and len(line) < 35:
                    result["action_breakdown"].append(line)

        # 3. Recent Recruiter Activities
        i = 0
        while i < len(lines) - 4:
            if lines[i] in ["HR Recruiter", "Company Recruiter", "Consultant Recruiter"]:
                company = lines[i + 1]
                action = lines[i + 3]
                time_ago = lines[i + 4]
                if "ago" in time_ago.lower():
                    entry = f"• {company} — *{action}* ({time_ago})"
                    if entry not in result["recent_activities"]:
                        result["recent_activities"].append(entry)
                    i += 4
            i += 1

        # 4. Top Keywords Appeared For
        if "Top keywords you appeared for" in lines:
            idx = lines.index("Top keywords you appeared for") + 1
            while idx < len(lines) - 1:
                item = lines[idx]
                count = lines[idx + 1]
                if "times" in count.lower():
                    result["top_keywords"].append(f"• {item}: `{count}`")
                    idx += 2
                else:
                    break

        # 5. Trending Relevant Skills
        if "Top skills searched by recruiters that are relevant to your profile" in lines:
            idx = lines.index("Top skills searched by recruiters that are relevant to your profile") + 1
            while idx < len(lines) - 1:
                item = lines[idx]
                count = lines[idx + 1]
                if "times" in count.lower():
                    result["trending_skills"].append(f"• {item}: `{count}`")
                    idx += 2
                else:
                    break

        logger.info(
            f"✅ Parsed analytics: {result['overall_summary'] or 'Metrics fetched'}"
        )

    except Exception as exc:
        logger.warning(f"Could not parse performance metrics: {exc}")

    return result
