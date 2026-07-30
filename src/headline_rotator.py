"""
Headline keyword rotation strategy for Naukri.com.
Cycles through different headline variations to match diverse recruiter search queries.
"""

import hashlib
import logging
import random
from datetime import datetime

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .config import Config
from .utils import human_delay, human_type, take_screenshot

logger = logging.getLogger("naukri_updater")

NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"


def rotate_headline(page: Page, config: Config) -> bool:
    """
    Update the resume headline on Naukri.com profile.

    Strategy: Pick a headline variation based on the day, ensuring
    a different headline shows up on each run. This broadens the
    keyword surface area for recruiter searches.

    Returns True on success.
    """
    new_headline = _pick_headline(config.headlines)
    logger.info(f"📝 Rotating headline to: \"{new_headline}\"")

    # Ensure we're on the profile page
    if "profile" not in page.url.lower():
        page.goto(NAUKRI_PROFILE_URL, wait_until="domcontentloaded", timeout=30000)
        human_delay(2, 4)

    # ── Find and click the headline edit button ──
    try:
        # Look for the resume headline section
        headline_section = page.locator('.resumeHeadline').or_(
            page.locator('[class*="resumeHeadline"]')
        ).or_(
            page.locator('text="Resume Headline"').locator("..")
        )

        # Click the edit pencil icon
        edit_icon = headline_section.first.locator('.edit-icon').or_(
            headline_section.first.locator('[class*="edit"]')
        ).or_(
            headline_section.first.locator('span[class*="icon"]')
        )

        if edit_icon.first.is_visible(timeout=5000):
            edit_icon.first.click()
            logger.info("✏️  Clicked headline edit button")
            human_delay(1, 2)
        else:
            # Try clicking anywhere on the headline section
            headline_section.first.click()
            human_delay(1, 2)

    except Exception as exc:
        logger.warning(f"Could not find headline edit button: {exc}")
        # Try alternative: look for any edit icon on the page near "Resume Headline"
        try:
            page.locator('text="Resume Headline"').first.click()
            human_delay(1, 2)
        except Exception:
            screenshot_path = take_screenshot(page, config.screenshot_dir, "headline_edit_failed")
            logger.error(f"❌ Cannot find headline edit. Screenshot: {screenshot_path}")
            return False

    # ── Edit the headline text ──
    try:
        # Find the textarea or input for the headline
        headline_input = page.locator('.resumeHeadline textarea').or_(
            page.locator('textarea[placeholder*="headline"]')
        ).or_(
            page.locator('#resumeHeadlineTxt')
        ).or_(
            page.locator('textarea').first
        )

        headline_input.first.wait_for(state="visible", timeout=10000)

        # Clear existing content and type new headline
        headline_input.first.fill("")
        human_delay(0.5, 1)
        human_type(headline_input.first, new_headline)
        logger.info("✍️  Headline text updated")
        human_delay(1, 2)

    except Exception as exc:
        logger.error(f"❌ Could not edit headline text: {exc}")
        take_screenshot(page, config.screenshot_dir, "headline_input_failed")
        return False

    # ── Save the changes ──
    try:
        save_btn = page.locator('button:has-text("Save")').first
        save_btn.wait_for(state="visible", timeout=5000)
        save_btn.click()
        logger.info("💾 Clicked Save")
        human_delay(2, 4)

        # Check for success
        try:
            page.locator('text="successfully"').or_(
                page.locator('[class*="success"]')
            ).first.wait_for(state="visible", timeout=5000)
        except PlaywrightTimeout:
            pass  # Save may have worked without explicit success message

        logger.info("✅ Headline rotation complete!")
        return True

    except Exception as exc:
        logger.error(f"❌ Could not save headline: {exc}")
        take_screenshot(page, config.screenshot_dir, "headline_save_failed")
        return False


def _pick_headline(headlines: list[str]) -> str:
    """
    Deterministically pick a headline variation for today.
    Uses the day-of-year to cycle through headlines, ensuring variety.
    """
    if not headlines:
        return "Software Engineer"

    day_of_year = datetime.now().timetuple().tm_yday
    index = day_of_year % len(headlines)
    return headlines[index]
