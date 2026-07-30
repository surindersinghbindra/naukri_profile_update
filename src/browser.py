"""
Playwright browser setup and management.
Handles browser launch, context creation, and session persistence.
"""

import logging
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from .config import Config

logger = logging.getLogger("naukri_updater")


class BrowserManager:
    """Manages Playwright browser lifecycle with session persistence."""

    def __init__(self, config: Config):
        self.config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def start(self) -> Page:
        """Launch browser and return a ready-to-use page."""
        logger.info("🌐 Launching browser...")

        self._playwright = sync_playwright().start()

        # Launch Chromium with anti-detection settings
        self._browser = self._playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        # Ensure session storage directory exists
        session_dir = Path(self.config.session_dir)
        session_dir.mkdir(parents=True, exist_ok=True)
        storage_state = session_dir / "session.json"

        # Create context with realistic viewport and user agent
        context_kwargs = {
            "viewport": {"width": 1366, "height": 768},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "locale": "en-IN",
            "timezone_id": "Asia/Kolkata",
        }

        # Reuse session if available (avoids repeated login)
        if storage_state.is_file():
            logger.info("🔑 Reusing saved session...")
            context_kwargs["storage_state"] = str(storage_state)

        self._context = self._browser.new_context(**context_kwargs)

        # Block unnecessary resources to speed things up (headless only)
        # In visible mode, keep everything loaded so you can see the real UI
        if self.config.headless:
            self._context.route(
                "**/*.{png,jpg,jpeg,gif,svg,mp4,webm,woff,woff2,ttf}",
                lambda route: route.abort(),
            )

        self._page = self._context.new_page()
        self._page.set_default_timeout(30000)  # 30s timeout

        # Inject stealth scripts to mask automation flags and navigator.webdriver
        self._page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
            """
        )

        logger.info("✅ Browser ready (Stealth mode active)")
        return self._page

    def save_session(self) -> None:
        """Persist session cookies/storage for future runs."""
        if self._context:
            session_dir = Path(self.config.session_dir)
            session_dir.mkdir(parents=True, exist_ok=True)
            storage_path = str(session_dir / "session.json")
            try:
                self._context.storage_state(path=storage_path)
                logger.info("💾 Session saved for reuse")
            except Exception as exc:
                logger.warning(f"Could not save session: {exc}")

    def close(self) -> None:
        """Clean up browser resources."""
        try:
            if self._page and not self._page.is_closed():
                self._page.close()
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
            logger.info("🔒 Browser closed")
        except Exception as exc:
            logger.warning(f"Error during browser cleanup: {exc}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save_session()
        self.close()
        return False

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page
