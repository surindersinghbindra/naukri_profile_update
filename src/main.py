"""
Naukri.com Profile Refresh Automation — Main Entry Point.

Orchestrates the full profile update cycle:
  1. Launch browser
  2. Login to Naukri.com
  3. Upload resume (strongest freshness signal)
  4. Rotate resume headline keywords
  5. Update key skills
  6. Touch profile summary
  7. Send notification

Usage:
  python -m src.main              # Full update
  python -m src.main --dry-run    # Login only, no changes
"""

import argparse
import sys
import traceback
from datetime import datetime

from .browser import BrowserManager
from .config import load_config
from .db import init_db, save_performance_snapshot
from .headline_rotator import rotate_headline
from .login import login, LoginFailedError, OTPRequiredError, CaptchaRequiredError
from .notifier import Notifier
from .performance_parser import fetch_performance_metrics
from .profile_updater import update_key_skills, update_profile_summary
from .resume_uploader import upload_resume
from .utils import human_delay, setup_logging, take_screenshot


def main():
    """Run the full Naukri profile update cycle."""

    # Parse arguments
    parser = argparse.ArgumentParser(description="Naukri.com Profile Refresh Automation")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Login only — do not modify the profile",
    )
    parser.add_argument(
        "--no-jitter",
        action="store_true",
        help="Skip random schedule start delay jitter",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Profile ID to run (e.g. profile_1 or profile_2)",
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.profile)

    # Setup logging
    logger = setup_logging(config.log_level, config.log_dir)

    # Check if profile is enabled
    if not config.enable_profile:
        logger.info(f"⏭️  SKIPPED — Profile '{config.profile_id}' is disabled (ENABLE_PROFILE=false)")
        return 0

    # Apply random start delay jitter if configured and not disabled
    if not args.no_jitter and not args.dry_run:
        import random
        import time

        random_mins = random.randint(config.jitter_min_minutes, max(config.jitter_min_minutes, config.jitter_max_minutes))
        random_secs = random.randint(config.jitter_min_seconds, max(config.jitter_min_seconds, config.jitter_max_seconds))
        total_jitter_secs = (random_mins * 60) + random_secs

        if total_jitter_secs > 0:
            logger.info(
                f"🎲 Applying random start delay jitter: {random_mins}m {random_secs}s ({total_jitter_secs}s total)..."
            )
            time.sleep(total_jitter_secs)

    # Initialize notifier
    notifier = Notifier(config)

    logger.info("=" * 60)
    logger.info("🚀 Naukri Profile Refresh — Starting")
    logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    logger.info(f"🎯 Target Role: {config.target_role}")
    logger.info(f"📄 Resume: {config.resume_path}")
    logger.info(f"🔕 Dry Run: {args.dry_run}")
    logger.info("=" * 60)

    # Track results
    results = {
        "resume_uploaded": False,
        "headline_rotated": False,
        "headline_text": "",
        "skills_updated": False,
        "summary_updated": False,
    }

    browser_manager = BrowserManager(config)

    try:
        # ── Step 1: Launch browser ──
        page = browser_manager.start()

        # ── Step 2: Login ──
        try:
            login(page, config)
        except OTPRequiredError as exc:
            logger.error(f"🔒 {exc}")
            notifier.send_failure(str(exc))
            return 1
        except CaptchaRequiredError as exc:
            logger.error(f"🤖 {exc}")
            notifier.send_failure(str(exc))
            return 1
        except LoginFailedError as exc:
            logger.error(f"🔐 {exc}")
            notifier.send_failure(str(exc))
            return 1

        if args.dry_run:
            logger.info("🔕 Dry run mode — skipping profile modifications")
            logger.info("✅ Login verified successfully!")
            browser_manager.save_session()
            notifier.send_dry_run()
            return 0

        failures = []

        # ── Step 3: Upload resume (if enabled) ──
        logger.info("\n" + "─" * 40)
        logger.info("📄 STEP 1/4: Resume Upload")
        logger.info("─" * 40)
        if not config.enable_resume_upload:
            results["resume_status"] = "⏭️ Skipped (Disabled)"
            logger.info("⏭️  SKIPPED — resume upload is disabled (ENABLE_RESUME_UPLOAD=false)")
        else:
            try:
                results["resume_uploaded"] = upload_resume(page, config)
                if results["resume_uploaded"]:
                    results["resume_status"] = "✅ Uploaded"
                else:
                    results["resume_status"] = "❌ Failed"
                    failures.append("Step 1 (Resume Upload)")
            except Exception as exc:
                logger.error(f"Resume upload error: {exc}")
                results["resume_status"] = f"❌ Failed"
                failures.append("Step 1 (Resume Upload)")
                take_screenshot(page, config.screenshot_dir, "resume_error")

        human_delay(config.human_delay_min, config.human_delay_max)

        # ── Step 4: Rotate headline (if enabled) ──
        logger.info("\n" + "─" * 40)
        logger.info("📝 STEP 2/4: Headline Rotation")
        logger.info("─" * 40)
        if not config.should_rotate_headline:
            results["headline_status"] = "⏭️ Skipped (Disabled)"
            logger.info("⏭️  SKIPPED — headline rotation is disabled or HEADLINES is blank")
        else:
            try:
                results["headline_rotated"] = rotate_headline(page, config)
                if results["headline_rotated"]:
                    from .headline_rotator import _pick_headline
                    results["headline_text"] = _pick_headline(config.headlines)
                    results["headline_status"] = "✅ Rotated"
                else:
                    results["headline_status"] = "❌ Failed"
                    failures.append("Step 2 (Headline Rotation)")
            except Exception as exc:
                logger.error(f"Headline rotation error: {exc}")
                results["headline_status"] = f"❌ Failed"
                failures.append("Step 2 (Headline Rotation)")
                take_screenshot(page, config.screenshot_dir, "headline_error")

        human_delay(config.human_delay_min, config.human_delay_max)

        # ── Step 5: Update key skills (if enabled) ──
        logger.info("\n" + "─" * 40)
        logger.info("🔧 STEP 3/4: Key Skills Update")
        logger.info("─" * 40)
        if not config.should_update_skills:
            results["skills_status"] = "⏭️ Skipped (Disabled)"
            logger.info("⏭️  SKIPPED — skills update is disabled or KEY_SKILLS is blank")
        else:
            try:
                results["skills_updated"] = update_key_skills(page, config)
                if results["skills_updated"]:
                    results["skills_status"] = "✅ Updated"
                else:
                    results["skills_status"] = "❌ Failed"
                    failures.append("Step 3 (Key Skills Update)")
            except Exception as exc:
                logger.error(f"Skills update error: {exc}")
                results["skills_status"] = f"❌ Failed"
                failures.append("Step 3 (Key Skills Update)")
                take_screenshot(page, config.screenshot_dir, "skills_error")

        human_delay(config.human_delay_min, config.human_delay_max)

        # ── Step 6: Touch profile summary ──
        logger.info("\n" + "─" * 40)
        logger.info("📋 STEP 4/4: Profile Summary Touch")
        logger.info("─" * 40)
        try:
            results["summary_updated"] = update_profile_summary(page, config)
            if results["summary_updated"]:
                results["summary_status"] = "✅ Touched"
            else:
                results["summary_status"] = "❌ Failed"
                failures.append("Step 4 (Profile Summary)")
        except Exception as exc:
            logger.error(f"Summary update error: {exc}")
            results["summary_status"] = f"❌ Failed"
            failures.append("Step 4 (Profile Summary)")
            take_screenshot(page, config.screenshot_dir, "summary_error")

        results["failures"] = failures

        # ── Step 7: Save session & report ──
        browser_manager.save_session()

        # Determine overall result
        any_success = any([
            results["resume_uploaded"],
            results["headline_rotated"],
            results["skills_updated"],
            results["summary_updated"],
        ])

        logger.info("\n" + "=" * 60)
        if any_success:
            logger.info("🎉 Profile refresh COMPLETE!")
            logger.info(f"   📄 Resume:   {results['resume_status']}")
            logger.info(f"   📝 Headline: {results['headline_status']}")
            logger.info(f"   🔧 Skills:   {results['skills_status']}")
            logger.info(f"   📋 Summary:  {results['summary_status']}")
            notifier.send_success(results)

            # ── Step 7: Parse & Send Performance Metrics + DB Save ──
            try:
                perf_metrics = fetch_performance_metrics(page, config)
                notifier.send_performance_metrics(perf_metrics)

                if config.enable_db_storage:
                    save_performance_snapshot(perf_metrics, config)
            except Exception as exc:
                logger.warning(f"Could not fetch/send performance analytics: {exc}")

        else:
            logger.warning("⚠️  No updates were successful this run")
            notifier.send_failure("All update strategies failed. Check logs.")

        logger.info("=" * 60)
        return 0

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.error(f"💥 Unexpected error: {error_msg}")
        logger.error(traceback.format_exc())

        try:
            screenshot_path = take_screenshot(
                browser_manager.page, config.screenshot_dir, "fatal_error"
            )
            notifier.send_failure(error_msg, screenshot_path)
        except Exception:
            notifier.send_failure(error_msg)

        return 1

    finally:
        browser_manager.close()


if __name__ == "__main__":
    sys.exit(main())
