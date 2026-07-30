"""
Core profile update orchestrator for Naukri.com.
Handles key skills reordering and profile summary updates.
"""

import logging
import random
from datetime import datetime

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .config import Config
from .utils import human_delay, human_type, take_screenshot

logger = logging.getLogger("naukri_updater")

NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"


def update_key_skills(page: Page, config: Config) -> bool:
    """
    Reorder/toggle key skills on the Naukri profile.

    Even reordering skills triggers a "profile modified" event,
    which refreshes the profile timestamp in the recruiter database.
    """
    logger.info("🔧 Updating key skills...")

    # Ensure we're on the profile page
    if "profile" not in page.url.lower():
        page.goto(NAUKRI_PROFILE_URL, wait_until="domcontentloaded", timeout=30000)
        human_delay(2, 4)

    try:
        # Find the key skills section
        skills_section = page.locator('.keySkills').or_(
            page.locator('[class*="keySkills"]')
        ).or_(
            page.locator('[class*="key-skills"]')
        ).or_(
            page.locator('text="Key Skills"').locator('..')
        )

        # Click edit icon
        edit_icon = skills_section.first.locator('.edit-icon').or_(
            skills_section.first.locator('[class*="edit"]')
        ).or_(
            skills_section.first.locator('span[class*="icon"]')
        )

        if edit_icon.first.is_visible(timeout=5000):
            edit_icon.first.click()
        else:
            skills_section.first.click()

        logger.info("✏️  Opened key skills editor")
        human_delay(2, 3)

    except Exception as exc:
        logger.warning(f"Could not open key skills editor: {exc}")
        return False

    # ── Strategy: Add a skill, then save ──
    # Shuffling existing skills is enough to trigger an update
    try:
        # Find the skills input field
        skills_input = page.locator('.keySkills input[type="text"]').or_(
            page.locator('input[placeholder*="skill"]')
        ).or_(
            page.locator('input[placeholder*="Skill"]')
        ).or_(
            page.locator('.chipInput input')
        )

        if skills_input.first.is_visible(timeout=5000):
            # Pick a random skill from the config that might not be there
            shuffled = config.key_skills.copy()
            random.shuffle(shuffled)
            new_skill = shuffled[0] if shuffled else "Python"

            human_type(skills_input.first, new_skill)
            human_delay(0.5, 1)

            # Press Enter to add the skill
            skills_input.first.press("Enter")
            human_delay(1, 2)

            logger.info(f"➕ Added/refreshed skill: {new_skill}")

    except Exception as exc:
        logger.warning(f"Could not modify skills input: {exc}")

    # ── Save ──
    try:
        save_btn = page.locator('button:has-text("Save")').first
        save_btn.wait_for(state="visible", timeout=5000)
        save_btn.click()
        logger.info("💾 Skills saved")
        human_delay(2, 3)

        logger.info("✅ Key skills updated!")
        return True

    except Exception as exc:
        logger.error(f"❌ Could not save skills: {exc}")
        take_screenshot(page, config.screenshot_dir, "skills_save_failed")

        # Try pressing Escape to close the modal
        page.keyboard.press("Escape")
        return False


def update_profile_summary(page: Page, config: Config) -> bool:
    """
    Make a minor update to the profile summary.

    Appends/modifies a timestamp at the end of the summary to trigger
    a "profile modified" event. Uses zero-width characters to be invisible.
    """
    logger.info("📝 Updating profile summary...")

    if "profile" not in page.url.lower():
        page.goto(NAUKRI_PROFILE_URL, wait_until="domcontentloaded", timeout=30000)
        human_delay(2, 4)

    try:
        # Find the profile summary section
        summary_section = page.locator('.profileSummary').or_(
            page.locator('[class*="profileSummary"]')
        ).or_(
            page.locator('[class*="profile-summary"]')
        ).or_(
            page.locator('text="Profile Summary"').locator('..')
        )

        # Click edit
        edit_icon = summary_section.first.locator('.edit-icon').or_(
            summary_section.first.locator('[class*="edit"]')
        )

        if edit_icon.first.is_visible(timeout=5000):
            edit_icon.first.click()
        else:
            summary_section.first.click()

        logger.info("✏️  Opened profile summary editor")
        human_delay(1, 2)

    except Exception as exc:
        logger.warning(f"Could not open profile summary editor: {exc}")
        return False

    try:
        # Find the textarea
        summary_input = page.locator('.profileSummary textarea').or_(
            page.locator('textarea[placeholder*="summary"]')
        ).or_(
            page.locator('#profileSummaryTxt')
        ).or_(
            page.locator('textarea').first
        )

        summary_input.first.wait_for(state="visible", timeout=10000)

        # Get current content
        current_text = summary_input.first.input_value()

        if current_text:
            # Remove any existing zero-width characters + timestamps at the end
            import re
            cleaned = re.sub(r'[\u200b\u200c\u200d\ufeff]+\d*$', '', current_text).rstrip()

            # Append invisible timestamp
            timestamp = datetime.now().strftime('%m%d%H')
            updated_text = f"{cleaned}\u200b{timestamp}"

            summary_input.first.fill("")
            human_delay(0.5, 1)
            human_type(summary_input.first, updated_text)
            logger.info("✍️  Summary updated with invisible timestamp")
            human_delay(1, 2)

        # Save
        save_btn = page.locator('button:has-text("Save")').first
        save_btn.wait_for(state="visible", timeout=5000)
        save_btn.click()
        logger.info("💾 Summary saved")
        human_delay(2, 3)

        logger.info("✅ Profile summary updated!")
        return True

    except Exception as exc:
        logger.error(f"❌ Could not update summary: {exc}")
        take_screenshot(page, config.screenshot_dir, "summary_update_failed")
        page.keyboard.press("Escape")
        return False
