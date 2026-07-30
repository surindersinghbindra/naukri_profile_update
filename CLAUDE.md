# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Playwright-based browser automation that logs into Naukri.com and refreshes a job-seeker profile (resume re-upload, headline rotation, key-skills reorder, summary touch) to keep it surfacing in recruiter searches. It also scrapes the Naukri "performance" analytics page, persists snapshots to PostgreSQL (SQLite fallback), sends Telegram notifications, and exposes a Streamlit dashboard. Supports two independent Naukri accounts (`profile_1`, `profile_2`) via isolated `.env` files, session storage, and Docker services.

## Commands

### Local run (no Docker)
```bash
source venv/bin/activate
python -m src.main --profile profile_1 --dry-run    # login-only smoke test, no profile changes
python -m src.main --profile profile_1 --no-jitter   # full run, skip random start delay
python -m src.main --profile profile_2               # full run with jitter (as cron would do)

# Or the wrapper that forces a visible (non-headless) browser and handles venv/deps setup:
./scripts/run_local.sh --dry-run
```
There is no test suite, linter, or build step in this repo — verification is done by running the above against the live site (`--dry-run` is the safe way to check login/session logic without touching the profile).

### Docker (Postgres + both profile updaters + dashboard)
```bash
docker compose up -d --build
docker compose ps
docker compose logs -f updater-profile1
docker compose exec postgres psql -U naukri_user -d naukri_analytics -c "SELECT ... FROM performance_snapshots WHERE profile_id = 'profile_1';"
```

### Dashboard
```bash
streamlit run dashboard.py   # http://localhost:8501, also runs as its own docker-compose service
```

## Architecture

**Per-profile isolation is the central design constraint.** Everything — credentials, session cookies, resumes, logs, DB rows — is keyed by `profile_id` (`profile_1` / `profile_2`), so cross-profile state leakage is a bug class to watch for when touching config or storage paths.

- `src/config.py` — `load_config(profile_id)` is the single source of truth. It layers env loading: `profiles/<profile_id>/.env` (override) → process env → hardcoded defaults, and resolves `RESUME_PATH`, `LOG_DIR`, `SCREENSHOT_DIR`, `SESSION_DIR` to profile-specific paths unless explicitly overridden. `HEADLINES`/`KEY_SKILLS` have tri-state parsing: unset env var → use built-in defaults; explicitly set but empty → disable that feature entirely (empty list); set with values → use those values. Required: `NAUKRI_EMAIL`, `NAUKRI_PASSWORD` (exits with `sys.exit(1)` if missing).
- `src/main.py` — orchestrator. Sequence: launch browser → `login()` → (if `--dry-run`, save session and exit) → resume upload → headline rotation → key skills update → summary touch → save session → fetch performance metrics → save DB snapshot → send Telegram report. Each step is independently try/excepted so one failing step (e.g. resume upload) doesn't abort the rest; failures take a screenshot via `take_screenshot()` and continue. `ENABLE_PROFILE=false` short-circuits the whole run before browser launch (used to disable one profile without removing its Docker service).
- `src/browser.py` — `BrowserManager` launches Chromium with anti-detection args and injects stealth JS (masks `navigator.webdriver`, spoofs plugins/languages) to evade Naukri's bot detection. Reuses `storage_state` from `profiles/<id>/session_storage/session.json` when present to skip repeated logins; `save_session()` persists it after every run. In headless mode it blocks image/font/media requests for speed; in visible mode (`HEADLESS=false`, used by `run_local.sh`) nothing is blocked so the real UI renders.
- `src/login.py` — checks `is_logged_in()` (navigate to profile URL, see if redirected to login) before attempting credential login, since a valid saved session avoids re-authenticating (Naukri's OTP/CAPTCHA challenges are a real risk on repeated logins). Raises distinct `OTPRequiredError` / `CaptchaRequiredError` / `LoginFailedError` — these require manual intervention (Naukri challenge cleared by hand, then automation restarted) and are not auto-retried in `main.py`.
- `src/resume_uploader.py`, `headline_rotator.py`, `profile_updater.py` — DOM interaction modules. Naukri's frontend selectors are unstable, so these lean on multiple fallback locators. `ENABLE_RESUME_UPLOAD=false` is the "safe mode" that touches headline/skills/summary only, avoiding any file upload risk while still refreshing the profile's recruiter-visible timestamp.
- `src/performance_parser.py` — scrapes `naukri.com/mnjuser/performance` for recruiter action counts, top search keywords, and trending skills; returns a dict consumed by both `notifier.py` (Telegram formatting) and `db.py` (regex-parses the same dict strings into structured rows — see `save_performance_snapshot`).
- `src/db.py` — `get_db_connection()` tries PostgreSQL first (`psycopg` v3, falling back to `psycopg2`), then falls back to a local SQLite file at `<log_dir>/analytics.db` if Postgres is unreachable — this makes local (non-Docker) runs work without a Postgres server. Schema creation (`init_db`) is idempotent and profile-aware (`profile_id` column on `performance_snapshots`).
- `src/utils.py` — `human_delay()`, curved-path `human_mouse_move()`, and other timing/movement helpers used throughout to mimic human interaction and reduce bot-detection risk; treat these as required, not optional, when adding new page interactions.
- `dashboard.py` — Streamlit app reading directly from the same DB layer/tables as `db.py`, with a profile switcher and an on-demand "run now" stepper that shells out to `src/main.py`.

### Docker/deployment shape
`docker-compose.yml` defines 4 services: `postgres`, `updater-profile1`, `updater-profile2`, `dashboard` — each updater service mounts its own `profiles/<id>/.env`, `resumes/`, and `session_storage/` directories, and shares one Postgres instance distinguished by `profile_id`. `scripts/entrypoint.sh` installs a cron job from `CRON_SCHEDULE` inside the container (env vars are dumped to a file since cron runs in a minimal environment) and optionally runs once immediately on startup (`RUN_ON_STARTUP`). `.github/workflows/deploy.yml` and `deploy-self-hosted.yml` auto-deploy on push to `main`/`master` via SSH or a self-hosted runner respectively (`docker compose down && docker compose up -d --build`).

## Working with this codebase

- Naukri's DOM/selectors change over time and this code already has fallback-selector patterns everywhere (e.g. `login.py`'s email/password/button lookups) — follow that pattern rather than relying on a single selector when touching page-interaction code.
- Session files (`profiles/*/session_storage/session.json`) and `.env` files contain live credentials/cookies — never print, log, or commit their contents.
- Prefer `--dry-run` for iterating on login/session logic; it verifies auth without risking a bad write to a real Naukri profile.
