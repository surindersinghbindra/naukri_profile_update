"""
Streamlit Control Panel & Performance Analytics Dashboard for Naukri.com.

Features:
1. 📊 Recruiter Analytics: Plotly charts & time-series performance tracking
2. ⚙️ Settings & Control Panel: Visual configuration editor with file upload, toggles, jitter & Telegram test
3. 🚀 Live Profile Refresh Stepper: Interactive step-by-step progress with pulsing beat animations & real-time log streaming

Usage:
    streamlit run dashboard.py
"""

import os
import re
import sqlite3
import subprocess
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from dotenv import load_dotenv

# Streamlit Page Config
st.set_page_config(
    page_title="Naukri Profile Updater — Control Panel & Analytics",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Stepper Pulsing Beat Animations and Terminals
st.markdown(
    """
    <style>
    @keyframes pulse-green {
        0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(46, 204, 113, 0.7); }
        50% { transform: scale(1.02); box-shadow: 0 0 15px 5px rgba(46, 204, 113, 0.5); }
        100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(46, 204, 113, 0); }
    }
    @keyframes pulse-blue {
        0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(52, 152, 219, 0.7); }
        50% { transform: scale(1.02); box-shadow: 0 0 15px 5px rgba(52, 152, 219, 0.5); }
        100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(52, 152, 219, 0); }
    }
    .step-active {
        animation: pulse-blue 1.5s infinite ease-in-out;
        border-left: 5px solid #3498db !important;
        background-color: rgba(52, 152, 219, 0.08) !important;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .step-completed {
        border-left: 5px solid #2ecc71 !important;
        background-color: rgba(46, 204, 113, 0.08) !important;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .step-skipped {
        border-left: 5px solid #95a5a6 !important;
        background-color: rgba(149, 165, 166, 0.05) !important;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .step-failed {
        border-left: 5px solid #e74c3c !important;
        background-color: rgba(231, 76, 60, 0.08) !important;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .step-pending {
        border-left: 5px solid #bdc3c7 !important;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
        opacity: 0.6;
    }
    .terminal-box {
        background-color: #0e1117;
        color: #00ff66;
        font-family: 'Courier New', Courier, monospace;
        padding: 15px;
        border-radius: 8px;
        height: 350px;
        overflow-y: auto;
        font-size: 13px;
        line-height: 1.5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_env_file(filepath: str = ".env") -> dict:
    """Read .env file as a key-value dictionary."""
    env_vars = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars


def save_env_file(env_vars: dict, filepath: str = ".env") -> None:
    """Update .env file preserving existing values."""
    current_lines = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            current_lines = f.readlines()

    new_lines = []
    written_keys = set()

    for line in current_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in env_vars:
                new_lines.append(f"{key}={env_vars[key]}\n")
                written_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Append any new keys
    for k, v in env_vars.items():
        if k not in written_keys:
            new_lines.append(f"{k}={v}\n")

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def get_db_connection():
    """Connect to PostgreSQL or fallback SQLite."""
    pg_host = os.getenv("POSTGRES_HOST", "postgres")
    if pg_host == "postgres" and not os.path.exists("/.dockerenv"):
        pg_host = "localhost"

    # Try psycopg v3
    try:
        import psycopg

        conn = psycopg.connect(
            dbname=os.getenv("POSTGRES_DB", "naukri_analytics"),
            user=os.getenv("POSTGRES_USER", "naukri_user"),
            password=os.getenv("POSTGRES_PASSWORD", "naukri_secure_password_123"),
            host=pg_host,
            port=os.getenv("POSTGRES_PORT", "5432"),
            connect_timeout=3,
        )
        return conn, "postgres"
    except Exception:
        pass

    # Try psycopg2 v2
    try:
        import psycopg2

        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "naukri_analytics"),
            user=os.getenv("POSTGRES_USER", "naukri_user"),
            password=os.getenv("POSTGRES_PASSWORD", "naukri_secure_password_123"),
            host=pg_host,
            port=os.getenv("POSTGRES_PORT", "5432"),
            connect_timeout=3,
        )
        return conn, "postgres"
    except Exception:
        pass

    # Fallback SQLite
    db_path = "logs/analytics.db"
    if os.path.exists(db_path):
        return sqlite3.connect(db_path), "sqlite"

    return None, None


# ── Title & Navigation Tabs ──
st.title("🎯 Naukri Profile Refresh & Control Panel")

tab_analytics, tab_settings, tab_stepper = st.tabs(
    ["📊 Recruiter Analytics", "⚙️ Settings & Control Panel", "🚀 Live Execution Stepper"]
)

def ensure_tables_exist(conn, db_type):
    """Ensure database schema tables exist so queries never fail on a fresh DB."""
    if not conn:
        return
    try:
        cur = conn.cursor()
        if db_type == "postgres":
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_snapshots (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    target_role VARCHAR(255),
                    overall_summary TEXT,
                    total_actions INT DEFAULT 0,
                    weekly_trend_pct INT DEFAULT 0,
                    trend_direction VARCHAR(20) DEFAULT 'stable'
                );

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
            conn.commit()
        else:  # sqlite
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS performance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    FOREIGN KEY(snapshot_id) REFERENCES performance_snapshots(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS top_keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER,
                    keyword TEXT NOT NULL,
                    appearance_count INTEGER NOT NULL,
                    FOREIGN KEY(snapshot_id) REFERENCES performance_snapshots(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS trending_skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER,
                    skill_name TEXT NOT NULL,
                    search_count_str TEXT,
                    search_count_num INTEGER,
                    FOREIGN KEY(snapshot_id) REFERENCES performance_snapshots(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS recruiter_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER,
                    company_name TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    time_ago_str TEXT,
                    FOREIGN KEY(snapshot_id) REFERENCES performance_snapshots(id) ON DELETE CASCADE
                );
                """
            )
            conn.commit()
    except Exception as e:
        st.error(f"Error initializing DB schema: {e}")


# ==============================================================================
# TAB 1: 📊 RECRUITER ANALYTICS
# ==============================================================================
with tab_analytics:
    st.header("📊 Recruiter Search Visibility & Performance Insights")

    conn, db_type = get_db_connection()

    if conn is None:
        st.warning(
            "⚠️ No database connection available. Run the profile updater at least once to generate metrics."
        )
        st.info("Trigger a run in the **🚀 Live Execution Stepper** tab!")
    else:
        st.caption(f"Connected Database Engine: **{db_type.upper()}**")
        ensure_tables_exist(conn, db_type)
        try:
            df_snapshots = pd.read_sql_query(
                "SELECT * FROM performance_snapshots ORDER BY timestamp ASC", conn
            )

            if df_snapshots.empty:
                st.info("ℹ️ Database tables ready. Trigger your first run to populate data.")
            else:
                df_breakdowns = pd.read_sql_query(
                    "SELECT b.*, s.timestamp FROM action_breakdowns b JOIN performance_snapshots s ON b.snapshot_id = s.id ORDER BY s.timestamp ASC",
                    conn,
                )
                df_keywords = pd.read_sql_query(
                    "SELECT k.*, s.timestamp FROM top_keywords k JOIN performance_snapshots s ON k.snapshot_id = s.id ORDER BY k.appearance_count DESC",
                    conn,
                )
                df_skills = pd.read_sql_query(
                    "SELECT sk.*, s.timestamp FROM trending_skills sk JOIN performance_snapshots s ON sk.snapshot_id = s.id ORDER BY sk.search_count_num DESC",
                    conn,
                )
                df_activities = pd.read_sql_query(
                    "SELECT a.*, s.timestamp as snapshot_time FROM recruiter_activities a JOIN performance_snapshots s ON a.snapshot_id = s.id ORDER BY a.id DESC",
                    conn,
                )

                latest = df_snapshots.iloc[-1]

                # Metric Cards
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(
                    "Total Recruiter Actions",
                    latest["total_actions"],
                    delta=f"{latest['weekly_trend_pct']}% weekly"
                    if latest["weekly_trend_pct"]
                    else None,
                    delta_color="inverse" if latest.get("trend_direction") == "down" else "normal",
                )
                c2.metric("Target Role", latest.get("target_role", "N/A"))
                c3.metric("Last Refresh", str(latest["timestamp"])[:16])
                c4.metric("Snapshots Recorded", len(df_snapshots))

                st.divider()

                # Charts
                cl, cr = st.columns([2, 1])
                with cl:
                    st.subheader("📈 Recruiter Actions Trend")
                    fig_trend = px.line(
                        df_snapshots,
                        x="timestamp",
                        y="total_actions",
                        markers=True,
                        title="90-Day Rolling Recruiter Actions",
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)

                with cr:
                    st.subheader("🔢 Action Breakdown")
                    if not df_breakdowns.empty:
                        latest_b = df_breakdowns[df_breakdowns["snapshot_id"] == latest["id"]]
                        if not latest_b.empty:
                            fig_pie = px.pie(
                                latest_b, values="metric_count", names="metric_name", hole=0.4
                            )
                            st.plotly_chart(fig_pie, use_container_width=True)

                st.divider()

                ck, cs = st.columns(2)
                with ck:
                    st.subheader("🔑 Top Recruiter Search Keywords")
                    if not df_keywords.empty:
                        latest_kw = df_keywords[df_keywords["snapshot_id"] == latest["id"]]
                        if not latest_kw.empty:
                            fig_kw = px.bar(
                                latest_kw,
                                x="appearance_count",
                                y="keyword",
                                orientation="h",
                                text="appearance_count",
                                color="appearance_count",
                            )
                            fig_kw.update_layout(yaxis={"categoryorder": "total ascending"})
                            st.plotly_chart(fig_kw, use_container_width=True)

                with cs:
                    st.subheader("⚡ High Demand Relevant Skills")
                    if not df_skills.empty:
                        latest_sk = df_skills[df_skills["snapshot_id"] == latest["id"]]
                        if not latest_sk.empty:
                            fig_sk = px.bar(
                                latest_sk,
                                x="skill_name",
                                y="search_count_num",
                                text="search_count_str",
                                color="search_count_num",
                            )
                            st.plotly_chart(fig_sk, use_container_width=True)

                st.divider()

                st.subheader("💼 Recent Recruiter Activity Feed")
                if not df_activities.empty:
                    st.dataframe(
                        df_activities[["company_name", "action_type", "time_ago_str", "snapshot_time"]],
                        use_container_width=True,
                    )
        finally:
            conn.close()


# ==============================================================================
# TAB 2: ⚙️ SETTINGS & CONTROL PANEL
# ==============================================================================
with tab_settings:
    st.header("⚙️ Visual Configuration & Strategy Control Panel")
    st.caption("Manage credentials, strategy toggles, headlines, skills, schedule jitter, and Telegram alerts.")

    env_data = load_env_file()

    with st.form("config_form"):
        st.subheader("🔐 Naukri.com Credentials")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            naukri_email = st.text_input(
                "Naukri Login Email",
                value=env_data.get("NAUKRI_EMAIL", ""),
                help="Your primary login email address on Naukri.com",
            )
        with col_c2:
            naukri_password = st.text_input(
                "Naukri Password",
                value=env_data.get("NAUKRI_PASSWORD", ""),
                type="password",
                help="Stored securely in .env",
            )

        st.divider()

        st.subheader("📄 Resume Upload & Safe Profile-Toggling Strategy")
        st.info("💡 **Safe Profile-Toggling Mode**: Disabling resume upload grants 100% of the Resdex recency rank boost via text updates while carrying zero file upload risk!")

        col_r1, col_r2 = st.columns([1, 2])
        with col_r1:
            enable_resume = st.toggle(
                "Enable Resume Upload",
                value=env_data.get("ENABLE_RESUME_UPLOAD", "true").lower() == "true",
                help="Turn OFF for Safe Profile-Toggling Mode",
            )
        with col_r2:
            resume_path_val = st.text_input(
                "Resume File Path",
                value=env_data.get("RESUME_PATH", "resumes/resume.pdf"),
            )

        # File Uploader Widget to Upload PDF directly in UI
        uploaded_pdf = st.file_uploader("Upload New Resume PDF", type=["pdf"])
        if uploaded_pdf is not None:
            resumes_dir = Path("resumes")
            resumes_dir.mkdir(parents=True, exist_ok=True)
            save_dest = resumes_dir / uploaded_pdf.name
            with open(save_dest, "wb") as f:
                f.write(uploaded_pdf.getbuffer())
            resume_path_val = str(save_dest)
            st.success(f"✅ Uploaded resume saved to `{save_dest}`")

        st.divider()

        st.subheader("🎯 Target Role & Profile Toggles")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            target_role = st.text_input("Target Role", value=env_data.get("TARGET_ROLE", "Senior Android Engineer"))
        with col_s2:
            enable_headline = st.toggle("Enable Headline Rotation", value=env_data.get("ENABLE_HEADLINE_ROTATION", "true").lower() == "true")
        with col_s3:
            enable_skills = st.toggle("Enable Key Skills Update", value=env_data.get("ENABLE_SKILLS_UPDATE", "true").lower() == "true")

        st.subheader("📝 Headline Rotation Variations")
        headlines_val = st.text_area(
            "Headline Variations (Comma-separated)",
            value=env_data.get("HEADLINES", ""),
            height=100,
            help="Include strong recruiter keywords for your role",
        )

        st.subheader("🔧 Key Skills Keywords")
        skills_val = st.text_area(
            "Key Skills List (Comma-separated)",
            value=env_data.get("KEY_SKILLS", ""),
            height=100,
        )

        st.divider()

        st.subheader("⏰ Schedule & Random Start Delay Jitter")
        col_sc1, col_sc2 = st.columns([1, 2])
        with col_sc1:
            cron_schedule_val = st.text_input("Cron Schedule", value=env_data.get("CRON_SCHEDULE", "0 8 * * *"))
            preset = st.selectbox(
                "Cron Presets",
                ["Custom", "Daily at 8:00 AM IST (0 8 * * *)", "Twice Daily 8 AM & 6 PM (0 8,18 * * *)", "Every 6 Hours (0 */6 * * *)"],
            )
            if "8:00 AM" in preset:
                cron_schedule_val = "0 8 * * *"
            elif "Twice Daily" in preset:
                cron_schedule_val = "0 8,18 * * *"
            elif "Every 6 Hours" in preset:
                cron_schedule_val = "0 */6 * * *"

        with col_sc2:
            st.caption("🎲 **Random Start Delay Jitter**: Adds random minutes/seconds to your scheduled run to make execution undetectable.")
            j_col1, j_col2 = st.columns(2)
            with j_col1:
                jitter_min_m = st.slider("Min Minutes Delay", 0, 59, int(env_data.get("SCHEDULE_JITTER_MIN_MINUTES", "0")))
                jitter_max_m = st.slider("Max Minutes Delay", 0, 59, int(env_data.get("SCHEDULE_JITTER_MAX_MINUTES", "15")))
            with j_col2:
                jitter_min_s = st.slider("Min Seconds Delay", 0, 59, int(env_data.get("SCHEDULE_JITTER_MIN_SECONDS", "0")))
                jitter_max_s = st.slider("Max Seconds Delay", 0, 59, int(env_data.get("SCHEDULE_JITTER_MAX_SECONDS", "59")))

        st.divider()

        st.subheader("📱 Telegram Bot Notifications")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            telegram_token = st.text_input("Telegram Bot Token", value=env_data.get("TELEGRAM_BOT_TOKEN", ""))
        with col_t2:
            telegram_chat = st.text_input("Telegram Chat ID", value=env_data.get("TELEGRAM_CHAT_ID", ""))

        st.divider()

        submit_save = st.form_submit_button("💾 Save Configuration", type="primary")

        if submit_save:
            updated = {
                "NAUKRI_EMAIL": naukri_email,
                "NAUKRI_PASSWORD": naukri_password,
                "ENABLE_RESUME_UPLOAD": "true" if enable_resume else "false",
                "RESUME_PATH": resume_path_val,
                "TARGET_ROLE": target_role,
                "ENABLE_HEADLINE_ROTATION": "true" if enable_headline else "false",
                "HEADLINES": headlines_val.strip(),
                "ENABLE_SKILLS_UPDATE": "true" if enable_skills else "false",
                "KEY_SKILLS": skills_val.strip(),
                "CRON_SCHEDULE": cron_schedule_val,
                "SCHEDULE_JITTER_MIN_MINUTES": str(jitter_min_m),
                "SCHEDULE_JITTER_MAX_MINUTES": str(jitter_max_m),
                "SCHEDULE_JITTER_MIN_SECONDS": str(jitter_min_s),
                "SCHEDULE_JITTER_MAX_SECONDS": str(jitter_max_s),
                "TELEGRAM_BOT_TOKEN": telegram_token,
                "TELEGRAM_CHAT_ID": telegram_chat,
            }
            save_env_file(updated)
            st.success("✅ Configuration saved to `.env` successfully!")
            time.sleep(1)
            st.rerun()

    # Telegram Connection Test Button
    st.subheader("🧪 Telegram Connection Test")
    if st.button("📱 Test Telegram Connection"):
        t_token = env_data.get("TELEGRAM_BOT_TOKEN")
        t_chat = env_data.get("TELEGRAM_CHAT_ID")
        if not t_token or not t_chat:
            st.error("Please enter both TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID above.")
        else:
            url = f"https://api.telegram.org/bot{t_token}/sendMessage"
            payload = {
                "chat_id": t_chat,
                "text": "📱 *Naukri Control Panel*: Telegram Connection Test Successful! ✅",
                "parse_mode": "Markdown",
            }
            try:
                resp = requests.post(url, json=payload, timeout=5)
                if resp.status_code == 200:
                    st.success("🎉 Test message sent successfully to your Telegram!")
                else:
                    st.error(f"Telegram API Error: {resp.text}")
            except Exception as e:
                st.error(f"Could not connect to Telegram: {e}")


# ==============================================================================
# TAB 3: 🚀 LIVE PROFILE REFRESH STEPPER WITH PULSING BEAT ANIMATIONS
# ==============================================================================
with tab_stepper:
    st.header("🚀 Live Interactive Profile Refresh Stepper")
    st.caption("Trigger an on-demand profile refresh with real-time visual step tracking, pulsing beat animation, and live terminal log output.")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        run_full = st.button("🚀 Run Full Profile Refresh Now", type="primary", use_container_width=True)
    with col_b2:
        run_dry = st.button("🧪 Run Dry Run (Login Test Only)", use_container_width=True)

    # Initial Stepper State
    steps = [
        {"id": 1, "name": "🔐 Step 1: Login & Session Auth", "status": "pending", "desc": "Authenticates or reuses saved session cookies"},
        {"id": 2, "name": "📄 Step 2: Resume Upload", "status": "pending", "desc": "Human UI navigation & OS file chooser upload"},
        {"id": 3, "name": "📝 Step 3: Headline Keyword Rotation", "status": "pending", "desc": "Rotates high-intent target role keywords"},
        {"id": 4, "name": "🔧 Step 4: Key Skills Reorder", "status": "pending", "desc": "Toggles skills to trigger profile modification"},
        {"id": 5, "name": "📋 Step 5: Profile Summary Touch", "status": "pending", "desc": "Appends invisible timestamp to summary"},
        {"id": 6, "name": "📊 Step 6: Performance Analytics & Telegram", "status": "pending", "desc": "Parses recruiter search views & sends Telegram report"},
    ]

    stepper_placeholder = st.empty()
    terminal_placeholder = st.empty()

    def render_stepper(current_steps):
        with stepper_placeholder.container():
            st.subheader("⚡ Live Step Execution Tracker")
            sc1, sc2, sc3 = st.columns(3)

            for idx, s in enumerate(current_steps):
                status_class = f"step-{s['status']}"
                status_badge = {
                    "pending": "⏳ Pending",
                    "active": "💥 IN PROGRESS (PULSING)",
                    "completed": "✅ Completed",
                    "skipped": "⏭️ Skipped",
                    "failed": "❌ Failed",
                }.get(s["status"], "⏳")

                col_target = sc1 if idx < 2 else (sc2 if idx < 4 else sc3)

                with col_target:
                    col_target.markdown(
                        f"""
                        <div class="{status_class}">
                            <strong>{s['name']}</strong><br/>
                            <small>{s['desc']}</small><br/>
                            <span style="font-weight:bold;">{status_badge}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    render_stepper(steps)

    if run_full or run_dry:
        cmd = ["python", "-m", "src.main", "--no-jitter"]
        if run_dry:
            cmd.append("--dry-run")

        st.info(f"Executing: `{' '.join(cmd)}`")

        # Initial Active state for Step 1
        steps[0]["status"] = "active"
        render_stepper(steps)

        log_lines = []

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            for line in process.stdout:
                log_lines.append(line.strip())

                # Live Stepper Status Parser based on Log Signals
                line_str = line.strip()

                if "Logging in to Naukri.com" in line_str or "Reusing saved session" in line_str:
                    steps[0]["status"] = "active"

                if "Already logged in" in line_str or "Login verified" in line_str or "Login successful" in line_str:
                    steps[0]["status"] = "completed"

                if "STEP 1/4: Resume Upload" in line_str:
                    steps[1]["status"] = "active"
                if "Resume uploaded successfully" in line_str:
                    steps[1]["status"] = "completed"
                if "resume upload is disabled" in line_str:
                    steps[1]["status"] = "skipped"

                if "STEP 2/4: Headline Rotation" in line_str:
                    steps[2]["status"] = "active"
                if "Headline rotated to" in line_str:
                    steps[2]["status"] = "completed"
                if "headline rotation is disabled" in line_str:
                    steps[2]["status"] = "skipped"

                if "STEP 3/4: Key Skills Update" in line_str:
                    steps[3]["status"] = "active"
                if "Key skills updated" in line_str:
                    steps[3]["status"] = "completed"
                if "skills update is disabled" in line_str:
                    steps[3]["status"] = "skipped"

                if "STEP 4/4: Profile Summary Touch" in line_str:
                    steps[4]["status"] = "active"
                if "Profile summary touch completed" in line_str:
                    steps[4]["status"] = "completed"

                if "Fetching performance & analytics" in line_str:
                    steps[5]["status"] = "active"
                if "Telegram notification sent" in line_str or "Saved performance snapshot" in line_str:
                    steps[5]["status"] = "completed"

                render_stepper(steps)

                # Render live streaming terminal box
                terminal_placeholder.markdown(
                    f'<div class="terminal-box">{"<br/>".join(log_lines[-20:])}</div>',
                    unsafe_allow_html=True,
                )

            process.wait()

            # Finalize any active steps to completed/done
            for s in steps:
                if s["status"] == "active":
                    s["status"] = "completed"
            render_stepper(steps)

            if process.returncode == 0:
                st.balloons()
                st.success("🎉 Execution finished successfully!")
            else:
                st.error("❌ Execution completed with warnings/errors.")

        except Exception as e:
            st.error(f"Error running subprocess: {e}")
