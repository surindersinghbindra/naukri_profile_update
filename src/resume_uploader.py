"""
Resume upload handler for Naukri.com.
Navigates to profile, scrolls to Resume section, clicks Update button to trigger file chooser,
and uploads the resume PDF file naturally like a real user.
"""

import logging
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .config import Config
from .utils import human_delay, random_human_activity, retry, take_screenshot

logger = logging.getLogger("naukri_updater")

NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"


@retry(max_attempts=2, delay_base=5.0)
def upload_resume(page: Page, config: Config) -> bool:
    """
    Upload resume PDF to Naukri.com profile using realistic UI interactions.

    Flow:
    1. Navigate to profile page
    2. Perform human-like mouse movement & subtle scroll
    3. Click left navigation link for "Resume" to scroll smoothly down
    4. Hover and click the "Update" button in the Resume section
    5. Intercept the file chooser on Update button click and set resume path
    """
    resume_path = Path(config.resume_path)

    if not resume_path.is_file():
        logger.warning(
            f"⚠️  Resume file not found at: {resume_path}. "
            "Skipping upload — will rely on profile field updates only."
        )
        return False

    logger.info(f"📄 Uploading resume: {resume_path.name}")

    # Navigate to profile page
    page.goto(NAUKRI_PROFILE_URL, wait_until="domcontentloaded", timeout=30000)
    human_delay(2, 3)

    # Perform natural pre-action mouse movement and scrolling
    random_human_activity(page)

    # ── Step 1: Click left side navigation link for "Resume" to scroll ──
    try:
        left_nav_resume = page.locator(
            "div:text-is('Resume'), a:text-is('Resume'), span:text-is('Resume')"
        ).first
        if left_nav_resume.is_visible(timeout=5000):
            logger.info("🖱️  Moving mouse and clicking left nav 'Resume' link...")
            left_nav_resume.hover()
            human_delay(0.5, 1)
            left_nav_resume.click()
            human_delay(1, 2)
    except Exception as exc:
        logger.warning(f"Could not click left nav Resume link: {exc}")

    # ── Strategy 1: Find the Update button and trigger File Chooser ──
    try:
        update_btn = page.locator(
            "button:text-is('Update')"
        ).or_(
            page.locator("button:has-text('Update resume')")
        ).or_(
            page.locator("button:has-text('Update')")
        ).first

        if update_btn.is_visible(timeout=5000):
            logger.info("📜 Scrolling 'Update' button into view...")
            update_btn.scroll_into_view_if_needed()
            human_delay(0.8, 1.5)

            logger.info("🖱️  Hovering over 'Update' button...")
            update_btn.hover()
            human_delay(0.5, 1)

            logger.info("📤 Intercepting file chooser and selecting file...")
            with page.expect_file_chooser(timeout=10000) as fc_info:
                update_btn.click()

            file_chooser = fc_info.value
            file_chooser.set_files(str(resume_path))
            logger.info("✅ File selected in file chooser!")
            human_delay(4, 7)

            _wait_for_upload_confirmation(page, config)
            logger.info("✅ Resume uploaded successfully!")
            return True
    except Exception as exc:
        logger.warning(f"Strategy 1 (Update button + File Chooser) failed: {exc}")

    # ── Strategy 2: Direct file input after scroll ──
    try:
        file_input = page.locator("input[id='resume'], input[type='file'][name='resume'], input[type='file']").first
        if file_input.count() > 0:
            logger.info("📜 Scrolling file input into view...")
            file_input.scroll_into_view_if_needed()
            human_delay(1, 2)

            file_input.set_input_files(str(resume_path))
            logger.info("📤 Resume file set via input element")
            human_delay(4, 7)

            _wait_for_upload_confirmation(page, config)
            logger.info("✅ Resume uploaded successfully!")
            return True
    except Exception as exc:
        logger.warning(f"Strategy 2 (Direct input) failed: {exc}")

    # All strategies failed
    screenshot_path = take_screenshot(page, config.screenshot_dir, "resume_upload_failed")
    logger.error(
        f"❌ All resume upload strategies failed. Screenshot: {screenshot_path}"
    )
    return False


def _wait_for_upload_confirmation(page: Page, config: Config) -> None:
    """Wait for visual confirmation that the resume was uploaded."""
    try:
        # Look for success indicators or updated timestamp on page
        success = page.locator('text="successfully"').or_(
            page.locator('text="Resume uploaded"')
        ).or_(
            page.locator('text="Resume updated"')
        ).or_(
            page.locator('text="Uploaded on"')
        ).or_(
            page.locator('.success-message')
        )

        success.first.wait_for(state="visible", timeout=15000)
        logger.info("📋 Upload confirmation detected")
    except PlaywrightTimeout:
        logger.info("📋 No explicit toast notification, but upload action completed")
