"""
Database Layer for Naukri Performance Analytics.
Handles PostgreSQL connection, automatic schema creation, transaction management,
and graceful fallback to SQLite for local runs when PostgreSQL is unreachable.
"""

import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .config import Config

logger = logging.getLogger("naukri_updater")


def _get_postgres_connection(config: Config):
    """Attempt connection to PostgreSQL (supports psycopg v3 and psycopg2 v2)."""
    host = config.postgres_host
    if host == "postgres" and not os.path.exists("/.dockerenv"):
        host = "localhost"

    # Try psycopg v3
    try:
        import psycopg

        conn = psycopg.connect(
            dbname=config.postgres_db,
            user=config.postgres_user,
            password=config.postgres_password,
            host=host,
            port=config.postgres_port,
            connect_timeout=5,
        )
        return conn, "postgres"
    except Exception:
        pass

    # Try psycopg2 v2
    try:
        import psycopg2

        conn = psycopg2.connect(
            dbname=config.postgres_db,
            user=config.postgres_user,
            password=config.postgres_password,
            host=host,
            port=config.postgres_port,
            connect_timeout=5,
        )
        return conn, "postgres"
    except Exception as exc:
        logger.debug(f"PostgreSQL connection attempt failed: {exc}")
        return None, None


def _get_sqlite_connection(config: Config):
    """Fallback to local SQLite database."""
    log_dir = Path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    db_path = log_dir / "analytics.db"
    conn = sqlite3.connect(str(db_path))
    return conn, "sqlite"


def get_db_connection(config: Config):
    """
    Get active database connection.
    Prefers PostgreSQL; falls back to local SQLite if PostgreSQL is unreachable.
    """
    if config.enable_db_storage:
        conn, db_type = _get_postgres_connection(config)
        if conn:
            return conn, db_type

        logger.info(
            "ℹ️  PostgreSQL not reachable. Falling back to local SQLite database (logs/analytics.db)."
        )
        return _get_sqlite_connection(config)

    return None, None


def init_db(config: Config) -> None:
    """Create database tables if they do not exist."""
    conn, db_type = get_db_connection(config)
    if not conn:
        return

    try:
        cur = conn.cursor()

        if db_type == "postgres":
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_snapshots (
                    id SERIAL PRIMARY KEY,
                    profile_id VARCHAR(50) DEFAULT 'profile_1',
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    target_role VARCHAR(255),
                    overall_summary TEXT,
                    total_actions INT DEFAULT 0,
                    weekly_trend_pct INT DEFAULT 0,
                    trend_direction VARCHAR(20) DEFAULT 'stable'
                );

                ALTER TABLE performance_snapshots ADD COLUMN IF NOT EXISTS profile_id VARCHAR(50) DEFAULT 'profile_1';

                CREATE TABLE IF NOT EXISTS action_breakdowns (
                    id SERIAL PRIMARY KEY,
                    snapshot_id INT REFERENCES performance_snapshots(id) ON DELETE CASCADE,
                    metric_name VARCHAR(100) NOT NULL,
                    metric_count INT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS top_keywords (
                    id SERIAL PRIMARY KEY,
                    snapshot_id INT REFERENCES performance_snapshots(id) ON DELETE CASCADE,
                    keyword VARCHAR(255) NOT NULL,
                    appearance_count INT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS trending_skills (
                    id SERIAL PRIMARY KEY,
                    snapshot_id INT REFERENCES performance_snapshots(id) ON DELETE CASCADE,
                    skill_name VARCHAR(255) NOT NULL,
                    search_count_str VARCHAR(50),
                    search_count_num INT
                );

                CREATE TABLE IF NOT EXISTS recruiter_activities (
                    id SERIAL PRIMARY KEY,
                    snapshot_id INT REFERENCES performance_snapshots(id) ON DELETE CASCADE,
                    company_name VARCHAR(255) NOT NULL,
                    action_type VARCHAR(100) NOT NULL,
                    time_ago_str VARCHAR(50)
                );
                """
            )
        else:  # sqlite
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS performance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT DEFAULT 'profile_1',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    target_role TEXT,
                    overall_summary TEXT,
                    total_actions INTEGER DEFAULT 0,
                    weekly_trend_pct INTEGER DEFAULT 0,
                    trend_direction TEXT DEFAULT 'stable'
                );

                CREATE TABLE IF NOT EXISTS action_breakdowns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER,
                    metric_name TEXT NOT NULL,
                    metric_count INTEGER NOT NULL,
                    FOREIGN KEY(snapshot_id) REFERENCES performance_snapshots(id)
                );

                CREATE TABLE IF NOT EXISTS top_keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER,
                    keyword TEXT NOT NULL,
                    appearance_count INTEGER NOT NULL,
                    FOREIGN KEY(snapshot_id) REFERENCES performance_snapshots(id)
                );

                CREATE TABLE IF NOT EXISTS trending_skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER,
                    skill_name TEXT NOT NULL,
                    search_count_str TEXT,
                    search_count_num INTEGER,
                    FOREIGN KEY(snapshot_id) REFERENCES performance_snapshots(id)
                );

                CREATE TABLE IF NOT EXISTS recruiter_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER,
                    company_name TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    time_ago_str TEXT,
                    FOREIGN KEY(snapshot_id) REFERENCES performance_snapshots(id)
                );
                """
            )
            # Migration check for SQLite
            try:
                cur.execute("ALTER TABLE performance_snapshots ADD COLUMN profile_id TEXT DEFAULT 'profile_1'")
            except Exception:
                pass

        conn.commit()
        cur.close()
        logger.info(f"✅ Database tables initialized ({db_type.upper()})")
    except Exception as exc:
        logger.warning(f"Failed to initialize database tables: {exc}")
    finally:
        conn.close()


def save_performance_snapshot(perf_data: Dict[str, Any], config: Config) -> Optional[int]:
    """
    Save performance metrics snapshot to database.
    Returns snapshot_id on success.
    """
    conn, db_type = get_db_connection(config)
    if not conn:
        return None

    try:
        # First ensure schema exists
        init_db(config)
        conn, db_type = get_db_connection(config)
        cur = conn.cursor()

        summary = perf_data.get("overall_summary", "")

        # Parse total actions count
        total_actions = 0
        actions_match = re.search(r"(\d+)\s+recruiter actions", summary, re.IGNORECASE)
        if actions_match:
            total_actions = int(actions_match.group(1))

        # Parse weekly trend %
        weekly_trend_pct = 0
        trend_direction = "stable"
        trend_match = re.search(r"(\d+)%\s+(less|more)\s+actions", summary, re.IGNORECASE)
        if trend_match:
            weekly_trend_pct = int(trend_match.group(1))
            trend_direction = "down" if trend_match.group(2).lower() == "less" else "up"

        # 1. Insert into performance_snapshots
        if db_type == "postgres":
            cur.execute(
                """
                INSERT INTO performance_snapshots
                (profile_id, target_role, overall_summary, total_actions, weekly_trend_pct, trend_direction)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (config.profile_id, config.target_role, summary, total_actions, weekly_trend_pct, trend_direction),
            )
            snapshot_id = cur.fetchone()[0]
        else:
            cur.execute(
                """
                INSERT INTO performance_snapshots
                (profile_id, target_role, overall_summary, total_actions, weekly_trend_pct, trend_direction)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (config.profile_id, config.target_role, summary, total_actions, weekly_trend_pct, trend_direction),
            )
            snapshot_id = cur.lastrowid

        param_mark = "%s" if db_type == "postgres" else "?"

        # 2. Insert Action Breakdowns
        for item in perf_data.get("action_breakdown", []):
            # Parse e.g. "5 Profile views" -> count=5, name="Profile views"
            match = re.search(r"^(\d+)\s+(.*)$", item.strip())
            if match:
                m_count = int(match.group(1))
                m_name = match.group(2).strip()
                cur.execute(
                    f"INSERT INTO action_breakdowns (snapshot_id, metric_name, metric_count) VALUES ({param_mark}, {param_mark}, {param_mark})",
                    (snapshot_id, m_name, m_count),
                )

        # 3. Insert Top Keywords
        for item in perf_data.get("top_keywords", []):
            # Parse e.g. "• Java: `15 times`"
            match = re.search(r"•\s*([^:]+):\s*`?(\d+)\s*times`?", item)
            if match:
                kw = match.group(1).strip()
                kw_count = int(match.group(2))
                cur.execute(
                    f"INSERT INTO top_keywords (snapshot_id, keyword, appearance_count) VALUES ({param_mark}, {param_mark}, {param_mark})",
                    (snapshot_id, kw, kw_count),
                )

        # 4. Insert Trending Skills
        for item in perf_data.get("trending_skills", []):
            # Parse e.g. "• React Native: `1K times`"
            match = re.search(r"•\s*([^:]+):\s*`?([^`\n]+)`?", item)
            if match:
                sk = match.group(1).strip()
                sk_str = match.group(2).strip()
                num_val = 0
                num_match = re.search(r"(\d+)([KkMb]?)", sk_str)
                if num_match:
                    val = int(num_match.group(1))
                    unit = num_match.group(2).upper()
                    mult = 1000 if unit == "K" else (1000000 if unit == "M" else 1)
                    num_val = val * mult

                cur.execute(
                    f"INSERT INTO trending_skills (snapshot_id, skill_name, search_count_str, search_count_num) VALUES ({param_mark}, {param_mark}, {param_mark}, {param_mark})",
                    (snapshot_id, sk, sk_str, num_val),
                )

        # 5. Insert Recruiter Activities
        for item in perf_data.get("recent_activities", []):
            # Parse e.g. "• Home Credit, Gurgaon — *Resume downloaded* (2d ago)"
            match = re.search(r"•\s*([^\u2014\-]+)[\u2014\-]\s*\*([^*]+)\*\s*\(([^)]+)\)", item)
            if match:
                comp = match.group(1).strip()
                action_t = match.group(2).strip()
                time_s = match.group(3).strip()
                cur.execute(
                    f"INSERT INTO recruiter_activities (snapshot_id, company_name, action_type, time_ago_str) VALUES ({param_mark}, {param_mark}, {param_mark}, {param_mark})",
                    (snapshot_id, comp, action_t, time_s),
                )

        conn.commit()
        cur.close()
        logger.info(f"💾 Saved performance snapshot #{snapshot_id} to database ({db_type.upper()})")
        return snapshot_id

    except Exception as exc:
        logger.warning(f"Error saving performance snapshot to database: {exc}")
        return None
    finally:
        conn.close()
