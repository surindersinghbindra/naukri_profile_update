"""
Notification system — Telegram Bot integration.
Sends success/failure alerts so you know the automation is working.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from .config import Config

logger = logging.getLogger("naukri_updater")


class Notifier:
    """Sends notifications via Telegram Bot API."""

    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.telegram_enabled
        self.bot_token = config.telegram_bot_token
        self.chat_id = config.telegram_chat_id

    def send_success(self, details: dict) -> None:
        """Send a success notification with update details."""
        if not self.enabled:
            logger.info("📱 Telegram not configured — skipping notification")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M IST")
        profile_name = self.config.profile_id.upper()

        message = (
            f"🎯 *Naukri Profile Updated! [{profile_name}]*\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"👤 *Profile*: `{profile_name}`\n"
            f"🕐 *Time*: `{timestamp}`\n\n"
            f"📄 Resume Upload: {details.get('resume_status', '⏭️ Skipped')}\n"
            f"📝 Headline Rotation: {details.get('headline_status', '⏭️ Skipped')}\n"
            f"🔧 Key Skills Update: {details.get('skills_status', '⏭️ Skipped')}\n"
            f"📋 Profile Summary: {details.get('summary_status', '⏭️ Skipped')}\n\n"
        )

        if details.get("failures"):
            message += f"⚠️ *Step Failures*:\n" + "\n".join([f"• {f}" for f in details["failures"]]) + "\n\n"

        if details.get("headline_text"):
            message += f"🏷️ *Active Headline*: _{details['headline_text']}_\n\n"

        message += f"💡 _Your profile is fresh on Resdex!_"
        self._send_message(message)

    def send_dry_run(self) -> None:
        """Send a notification when dry-run mode completes."""
        if not self.enabled:
            logger.info("📱 Telegram not configured — skipping dry run notification")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M IST")
        profile_name = self.config.profile_id.upper()
        message = (
            f"🔕 *Naukri Dry Run Verified! [{profile_name}]*\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"👤 *Profile*: `{profile_name}`\n"
            f"🕐 *Time*: `{timestamp}`\n\n"
            f"✅ Login status verified successfully\n"
            f"💾 Session cookies saved for reuse\n\n"
            f"💡 _No profile changes were made (Dry-Run Mode)._"
        )
        self._send_message(message)

    def send_performance_metrics(self, perf_data: dict) -> None:
        """Send formatted performance analytics to Telegram."""
        if not self.enabled:
            logger.info("📱 Telegram not configured — skipping performance notification")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M IST")
        profile_name = self.config.profile_id.upper()

        summary = perf_data.get("overall_summary") or "Analytics Summary"
        breakdown = "\n".join([f"• {b}" for b in perf_data.get("action_breakdown", [])])
        activities = "\n".join(perf_data.get("recent_activities", [])[:5])
        keywords = "\n".join(perf_data.get("top_keywords", [])[:5])
        skills = "\n".join(perf_data.get("trending_skills", [])[:5])

        message = (
            f"📊 *Naukri Performance Analytics [{profile_name}]*\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"👤 *Profile*: `{profile_name}`\n"
            f"🕐 *Time*: `{timestamp}`\n\n"
            f"📈 *Activity Overview*:\n_{summary}_\n"
        )

        if breakdown:
            message += f"\n🔢 *Breakdown*:\n{breakdown}\n"

        if activities:
            message += f"\n💼 *Recent Recruiter Actions*:\n{activities}\n"

        if keywords:
            message += f"\n🔑 *Top Search Keywords*:\n{keywords}\n"

        if skills:
            message += f"\n⚡ *Trending Relevant Skills*:\n{skills}\n"

        self._send_message(message)

    def send_failure(self, error: str, failed_step: Optional[str] = None, screenshot_path: Optional[str] = None) -> None:
        """Send a failure notification with error details."""
        if not self.enabled:
            logger.info("📱 Telegram not configured — skipping failure notification")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M IST")
        profile_name = self.config.profile_id.upper()

        message = (
            f"❌ *Naukri Update FAILED [{profile_name}]*\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"👤 *Profile*: `{profile_name}`\n"
            f"🕐 *Time*: `{timestamp}`\n\n"
        )

        if failed_step:
            message += f"📍 *Failed at Step*: `{failed_step}`\n"

        message += f"🔴 *Error*: `{error[:400]}`\n\n"
        message += f"💡 _Check logs/screenshots for details._"
        )

        self._send_message(message)

        # Send screenshot if available
        if screenshot_path and Path(screenshot_path).is_file():
            self._send_photo(screenshot_path, "Error screenshot")

    def send_startup(self) -> None:
        """Send a startup notification."""
        if not self.enabled:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M IST")
        message = (
            f"🚀 *Naukri Updater Started*\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp}\n"
            f"📅 Schedule: `{self.config.cron_schedule}`\n"
            f"🎯 Target: _{self.config.target_role}_"
        )
        self._send_message(message)

    def _send_message(self, text: str) -> bool:
        """Send a text message via Telegram Bot API."""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("📱 Telegram notification sent")
                return True
            else:
                logger.warning(
                    f"Telegram API error {response.status_code}: {response.text}"
                )
                return False
        except Exception as exc:
            logger.warning(f"Could not send Telegram notification: {exc}")
            return False

    def _send_photo(self, photo_path: str, caption: str = "") -> bool:
        """Send a photo via Telegram Bot API."""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"

        try:
            with open(photo_path, "rb") as photo:
                response = requests.post(
                    url,
                    data={"chat_id": self.chat_id, "caption": caption},
                    files={"photo": photo},
                    timeout=30,
                )

            if response.status_code == 200:
                logger.info("📱 Screenshot sent via Telegram")
                return True
            else:
                logger.warning(f"Telegram photo error: {response.text}")
                return False
        except Exception as exc:
            logger.warning(f"Could not send Telegram photo: {exc}")
            return False
