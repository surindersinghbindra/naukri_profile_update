"""
Configuration management for Naukri Profile Updater.
Loads and validates all settings from environment variables.
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


# Load .env file if present (local development)
load_dotenv()


@dataclass
class Config:
    """Centralized configuration loaded from environment variables."""

    # ── Profile ID & Enable Toggle ──
    profile_id: str = "profile_1"
    enable_profile: bool = True

    # ── Naukri Credentials ──
    naukri_email: str = ""
    naukri_password: str = ""

    # ── Resume ──
    enable_resume_upload: bool = True
    resume_path: str = "/app/resumes/resume.pdf"

    # ── Profile Strategy ──
    target_role: str = "Senior Software Engineer"
    enable_headline_rotation: bool = True
    headlines: list[str] = field(default_factory=list)
    enable_skills_update: bool = True
    key_skills: list[str] = field(default_factory=list)

    # ── Schedule & Start Delay Jitter ──
    cron_schedule: str = "0 8 * * *"
    jitter_min_minutes: int = 0
    jitter_max_minutes: int = 15
    jitter_min_seconds: int = 0
    jitter_max_seconds: int = 59

    # ── Telegram ──
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # ── Browser ──
    headless: bool = True

    # ── Behavior ──
    human_delay_min: float = 2.0
    human_delay_max: float = 5.0
    max_retries: int = 3
    log_level: str = "INFO"

    # ── Database ──
    enable_db_storage: bool = True
    postgres_db: str = "naukri_analytics"
    postgres_user: str = "naukri_user"
    postgres_password: str = "naukri_secure_password_123"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # ── Paths ──
    log_dir: str = "/app/logs"
    screenshot_dir: str = "/app/logs"
    session_dir: str = "/app/session_storage"

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def resume_file_exists(self) -> bool:
        return Path(self.resume_path).is_file()

    @property
    def should_rotate_headline(self) -> bool:
        """Only rotate if enabled AND headlines list is non-empty."""
        return self.enable_headline_rotation and bool(self.headlines)

    @property
    def should_update_skills(self) -> bool:
        """Only update skills if enabled AND skills list is non-empty."""
        return self.enable_skills_update and bool(self.key_skills)


def load_config(profile_id: Optional[str] = None) -> Config:
    """Load configuration from environment variables with validation."""
    if not profile_id:
        profile_id = os.getenv("PROFILE_ID", "profile_1")

    # Load profile-specific .env if present
    profile_env = Path(f"profiles/{profile_id}/.env")
    if profile_env.is_file():
        load_dotenv(str(profile_env), override=True)
    else:
        load_dotenv(override=True)

    def parse_list(env_var: str, default: str = "") -> list[str]:
        raw = os.getenv(env_var, default)
        return [item.strip() for item in raw.split(",") if item.strip()]

    # Parse human delay range
    human_delay_raw = os.getenv("HUMAN_DELAY_RANGE", "2,5")
    try:
        parts = [float(x.strip()) for x in human_delay_raw.split(",")]
        delay_min, delay_max = parts[0], parts[1]
    except Exception:
        delay_min, delay_max = 2.0, 5.0

    default_headlines = (
        "Senior Software Engineer | Python | AWS | Microservices,"
        "Full Stack Developer | Python | React | Cloud Native,"
        "Backend Engineer | Python | Django | REST APIs | AWS,"
        "Software Engineer | Distributed Systems | Python | Docker | K8s"
    )

    default_skills = (
        "Python,Django,Flask,FastAPI,React,JavaScript,TypeScript,"
        "AWS,Docker,Kubernetes,PostgreSQL,Redis,CI/CD,Microservices,REST APIs"
    )

    def parse_bool(env_var: str, default: str = "true") -> bool:
        return os.getenv(env_var, default).strip().lower() == "true"

    # If HEADLINES env var is explicitly set but empty, use empty list (skip rotation)
    # If HEADLINES env var is not set at all, use defaults
    raw_headlines = os.getenv("HEADLINES")
    if raw_headlines is None:
        headlines = parse_list("HEADLINES", default_headlines)
    elif raw_headlines.strip() == "":
        headlines = []
    else:
        headlines = parse_list("HEADLINES", "")

    raw_skills = os.getenv("KEY_SKILLS")
    if raw_skills is None:
        key_skills = parse_list("KEY_SKILLS", default_skills)
    elif raw_skills.strip() == "":
        key_skills = []
    else:
        key_skills = parse_list("KEY_SKILLS", "")

    raw_resume_path = os.getenv("RESUME_PATH", f"profiles/{profile_id}/resumes/resume.pdf")
    if raw_resume_path.startswith("/app/") and not Path(raw_resume_path).is_file():
        local_fallback = Path(raw_resume_path.replace("/app/", "./"))
        if local_fallback.is_file():
            raw_resume_path = str(local_fallback.resolve())

    default_log_dir = f"logs/{profile_id}"
    default_session_dir = f"profiles/{profile_id}/session_storage"

    config = Config(
        profile_id=profile_id,
        enable_profile=parse_bool("ENABLE_PROFILE", "true"),
        naukri_email=os.getenv("NAUKRI_EMAIL", ""),
        naukri_password=os.getenv("NAUKRI_PASSWORD", ""),
        enable_resume_upload=parse_bool("ENABLE_RESUME_UPLOAD", "true"),
        resume_path=raw_resume_path,
        target_role=os.getenv("TARGET_ROLE", "Senior Software Engineer"),
        enable_headline_rotation=parse_bool("ENABLE_HEADLINE_ROTATION", "true"),
        headlines=headlines,
        enable_skills_update=parse_bool("ENABLE_SKILLS_UPDATE", "true"),
        key_skills=key_skills,
        cron_schedule=os.getenv("CRON_SCHEDULE", "0 8 * * *"),
        jitter_min_minutes=int(os.getenv("SCHEDULE_JITTER_MIN_MINUTES", "0")),
        jitter_max_minutes=int(os.getenv("SCHEDULE_JITTER_MAX_MINUTES", "15")),
        jitter_min_seconds=int(os.getenv("SCHEDULE_JITTER_MIN_SECONDS", "0")),
        jitter_max_seconds=int(os.getenv("SCHEDULE_JITTER_MAX_SECONDS", "59")),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
        headless=parse_bool("HEADLESS", "true"),
        enable_db_storage=parse_bool("ENABLE_DB_STORAGE", "true"),
        postgres_db=os.getenv("POSTGRES_DB", "naukri_analytics"),
        postgres_user=os.getenv("POSTGRES_USER", "naukri_user"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "naukri_secure_password_123"),
        postgres_host=os.getenv("POSTGRES_HOST", "postgres"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        human_delay_min=delay_min,
        human_delay_max=delay_max,
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        log_dir=os.getenv("LOG_DIR", default_log_dir),
        screenshot_dir=os.getenv("SCREENSHOT_DIR", default_log_dir),
        session_dir=os.getenv("SESSION_DIR", default_session_dir),
    )

    # Validate required fields
    errors = []
    if not config.naukri_email:
        errors.append("NAUKRI_EMAIL is required")
    if not config.naukri_password:
        errors.append("NAUKRI_PASSWORD is required")

    if errors:
        print("❌ Configuration errors:", file=sys.stderr)
        for err in errors:
            print(f"   • {err}", file=sys.stderr)
        sys.exit(1)

    # Log what's enabled/disabled
    if not config.should_rotate_headline:
        print("ℹ️  Headline rotation: DISABLED (ENABLE_HEADLINE_ROTATION=false or HEADLINES is blank)")
    if not config.should_update_skills:
        print("ℹ️  Skills update: DISABLED (ENABLE_SKILLS_UPDATE=false or KEY_SKILLS is blank)")

    return config
