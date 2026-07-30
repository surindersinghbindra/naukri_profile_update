"""
Naukri.com login handler.
Handles email + password authentication with OTP/CAPTCHA detection.
"""

import logging

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .config import Config
from .utils import human_delay, human_type, take_screenshot

logger = logging.getLogger("naukri_updater")

NAUKRI_LOGIN_URL = "https://www.naukri.com/nlogin/login"
NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"


def is_logged_in(page: Page) -> bool:
    """Check if user is already logged in by detecting profile elements."""
    try:
        page.goto(NAUKRI_PROFILE_URL, wait_until="domcontentloaded", timeout=20000)
        human_delay(2, 3)

        current_url = page.url.lower()

        # If we stayed on the profile page (not redirected to login), we're logged in
        if "profile" in current_url and "login" not in current_url:
            logger.info("✅ Already logged in via saved session")
            return True

        # If redirected to login page, session has expired
        if "login" in current_url:
            logger.info("🔒 Session expired — need to login again")
            return False

    except Exception as exc:
        logger.warning(f"Session check failed: {exc}")

    return False


def login(page: Page, config: Config) -> bool:
    """
    Login to Naukri.com with email and password.

    Returns True on success, raises Exception on failure.
    """
    logger.info("🔐 Logging in to Naukri.com...")

    # Check if already logged in via saved session
    if is_logged_in(page):
        return True

    # Navigate to login page
    page.goto(NAUKRI_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    human_delay(2, 4)

    # ── Check if Naukri redirected us away from login (session still valid) ──
    current_url = page.url.lower()
    if "login" not in current_url:
        logger.info(f"✅ Redirected away from login (session valid). URL: {page.url}")
        return True

    # Enter email
    email_input = page.locator('input[placeholder="Enter your active Email ID / Username"]')
    if not email_input.is_visible(timeout=10000):
        # Try alternative selectors — Naukri changes these
        email_input = page.locator("#usernameField")

    email_input.fill("")
    human_delay(0.5, 1)
    human_type(email_input, config.naukri_email)
    logger.info(f"📧 Entered email: {config.naukri_email[:3]}***")
    human_delay(1, 2)

    # Enter password
    password_input = page.locator('input[placeholder="Enter your password"]')
    if not password_input.is_visible(timeout=5000):
        password_input = page.locator("#passwordField")

    password_input.fill("")
    human_delay(0.5, 1)
    human_type(password_input, config.naukri_password)
    logger.info("🔑 Entered password")
    human_delay(1, 2)

    # Click login button (exact match — avoids matching "Use OTP to Login")
    login_button = page.get_by_role("button", name="Login", exact=True)
    if not login_button.is_visible(timeout=5000):
        # Fallback: target the specific blue login button by class
        login_button = page.locator('button.blue-btn[type="submit"]')

    login_button.click()
    logger.info("🖱️  Clicked Login button")
    human_delay(3, 5)

    # ── Handle post-login scenarios ──

    # Check for OTP challenge
    try:
        otp_indicator = page.locator('text="Enter OTP"').or_(
            page.locator('text="Verify OTP"')
        ).or_(
            page.locator('input[placeholder*="OTP"]')
        )
        if otp_indicator.first.is_visible(timeout=3000):
            screenshot_path = take_screenshot(page, config.screenshot_dir, "otp_required")
            raise OTPRequiredError(
                "Naukri is requesting OTP verification. "
                "Please login manually once to clear the OTP challenge, "
                "then restart the automation."
            )
    except PlaywrightTimeout:
        pass  # No OTP challenge — continue

    # Check for CAPTCHA
    try:
        captcha_indicator = page.locator('iframe[title*="captcha"]').or_(
            page.locator('iframe[title*="reCAPTCHA"]')
        ).or_(
            page.locator("#captcha")
        )
        if captcha_indicator.first.is_visible(timeout=3000):
            screenshot_path = take_screenshot(page, config.screenshot_dir, "captcha_required")
            raise CaptchaRequiredError(
                "Naukri is showing a CAPTCHA. "
                "Please login manually once to clear it, "
                "then restart the automation."
            )
    except PlaywrightTimeout:
        pass  # No CAPTCHA — continue

    # Check for invalid credentials
    try:
        error_msg = page.locator('text="Invalid username or password"').or_(
            page.locator('.err-msg')
        ).or_(
            page.locator('text="Your password is incorrect"')
        )
        if error_msg.first.is_visible(timeout=3000):
            raise LoginFailedError("Invalid email or password. Check your .env file.")
    except PlaywrightTimeout:
        pass

    # Verify successful login — check if we're on the dashboard or profile
    try:
        page.wait_for_url("**/mnjuser/**", timeout=15000)
        logger.info("✅ Login successful!")
        return True
    except PlaywrightTimeout:
        pass

    # Alternative: check if navigation elements of logged-in state exist
    try:
        # Look for any indicator that we're logged in
        logged_in = page.locator('.nI-gNb-drawer__icon').or_(
            page.locator('a[href*="mnjuser"]')
        ).or_(
            page.locator('.view-profile-btn')
        )
        if logged_in.first.is_visible(timeout=10000):
            logger.info("✅ Login successful (detected via nav elements)!")
            return True
    except PlaywrightTimeout:
        pass

    # If we get here, login status is uncertain
    screenshot_path = take_screenshot(page, config.screenshot_dir, "login_uncertain")
    logger.warning(
        f"⚠️  Login status uncertain. Current URL: {page.url}. "
        f"Screenshot: {screenshot_path}. Attempting to continue..."
    )

    # Try navigating to profile to confirm
    page.goto(NAUKRI_PROFILE_URL, wait_until="domcontentloaded", timeout=20000)
    human_delay(2, 3)

    if "login" in page.url.lower():
        raise LoginFailedError("Login failed — redirected back to login page.")

    logger.info("✅ Login appears successful (navigated to profile)")
    return True


# ── Custom Exceptions ──


class LoginFailedError(Exception):
    """Raised when login credentials are invalid."""
    pass


class OTPRequiredError(Exception):
    """Raised when Naukri requires OTP verification."""
    pass


class CaptchaRequiredError(Exception):
    """Raised when Naukri shows a CAPTCHA challenge."""
    pass
