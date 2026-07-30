"""
Utility functions: logging setup, retry decorator, human-like delays, screenshots.
"""

import functools
import logging
import random
import time
import traceback
from datetime import datetime
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_dir: str = "/app/logs") -> logging.Logger:
    """Configure structured logging to both console and file."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    log_file = Path(log_dir) / f"naukri_update_{datetime.now().strftime('%Y-%m-%d')}.log"

    logger = logging.getLogger("naukri_updater")
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Prevent duplicate handlers on re-initialization
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def human_delay(min_seconds: float = 2.0, max_seconds: float = 5.0) -> None:
    """
    Sleep for a random duration to mimic human interaction patterns.
    This is critical for avoiding bot detection on Naukri.com.
    """
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def human_mouse_move(page, target_x: int, target_y: int, min_steps: int = 15, max_steps: int = 30) -> None:
    """
    Move mouse to target coordinates using smooth interpolated steps
    instead of instant teleportation.
    """
    try:
        steps = random.randint(min_steps, max_steps)
        page.mouse.move(target_x, target_y, steps=steps)
    except Exception:
        pass


def human_type(locator, text: str, min_delay_ms: float = 60, max_delay_ms: float = 180) -> None:
    """
    Type text one character at a time, dispatching real keydown/input/keyup
    events per keystroke with randomized inter-key delay — unlike Locator.fill(),
    which sets the value directly via CDP with no keystroke events at all.
    """
    for char in text:
        locator.press_sequentially(char)
        time.sleep(random.uniform(min_delay_ms, max_delay_ms) / 1000)


def random_human_activity(page) -> None:
    """
    Perform natural human-like pre-action behavior:
    1. Smooth random mouse movements across the screen
    2. Subtle mouse wheel scrolling
    3. Brief pauses between movements
    """
    try:
        logger = logging.getLogger("naukri_updater")
        logger.info("🖱️  Performing human-like mouse movement & scroll...")

        viewport = page.viewport_size or {"width": 1366, "height": 768}
        vw, vh = viewport["width"], viewport["height"]

        # Move mouse 2-4 times to random points across screen
        for _ in range(random.randint(2, 4)):
            rx = random.randint(150, max(200, vw - 150))
            ry = random.randint(150, max(200, vh - 150))
            human_mouse_move(page, rx, ry, min_steps=12, max_steps=25)
            time.sleep(random.uniform(0.3, 0.7))

        # Perform a slight random scroll wheel movement
        scroll_y = random.randint(120, 280)
        page.mouse.wheel(0, scroll_y)
        time.sleep(random.uniform(0.5, 1.2))

    except Exception as exc:
        logging.getLogger("naukri_updater").warning(f"Human activity simulation warning: {exc}")


def retry(max_attempts: int = 3, delay_base: float = 5.0):
    """
    Decorator that retries a function with exponential backoff.
    Useful for handling transient network issues or page load failures.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger("naukri_updater")
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    if attempt < max_attempts:
                        wait_time = delay_base * (2 ** (attempt - 1))
                        logger.warning(
                            f"⚠️  {func.__name__} failed (attempt {attempt}/{max_attempts}): "
                            f"{exc}. Retrying in {wait_time:.1f}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_attempts} attempts: {exc}"
                        )

            raise last_exception
        return wrapper
    return decorator


def take_screenshot(page, screenshot_dir: str, name: str = "error") -> str:
    """Capture a screenshot for debugging. Returns the file path."""
    Path(screenshot_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = str(Path(screenshot_dir) / f"{name}_{timestamp}.png")

    try:
        page.screenshot(path=filepath, full_page=True)
        logging.getLogger("naukri_updater").info(f"📸 Screenshot saved: {filepath}")
    except Exception as exc:
        logging.getLogger("naukri_updater").warning(f"Could not take screenshot: {exc}")
        filepath = ""

    return filepath


def get_timestamp_suffix() -> str:
    """Generate a short timestamp suffix for profile fields (invisible to recruiters)."""
    # Using a zero-width space + micro-timestamp to force a 'change' without visible impact
    return f"\u200b{datetime.now().strftime('%m%d')}"
