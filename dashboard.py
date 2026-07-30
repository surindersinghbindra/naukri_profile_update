"""
Streamlit Control Panel & Performance Analytics Dashboard for Naukri.com.

Features:
1. 📊 Recruiter Analytics: Plotly charts & time-series performance tracking per account profile
2. 🚀 Live Execution Stepper: Interactive step-by-step progress with pulsing beat animations & real-time log streaming for Profile 1 or Profile 2

Usage:
    streamlit run dashboard.py
"""

import os
import sqlite3
import subprocess
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Streamlit Page Config
st.set_page_config(
    page_title="Naukri Profile Refresh Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Stepper Pulsing Beat Animations and Terminal Output
st.markdown(
    """
    <style>
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
    db_path = "logs/profile_1/analytics.db"
    if not os.path.exists(db_path):
        db_path = "logs/analytics.db"
    if os.path.exists(db_path):
        return sqlite3.connect(db_path), "sqlite"

    return None, None


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
            conn.commit()
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
            try:
                cur.execute("ALTER TABLE performance_snapshots ADD COLUMN profile_id TEXT DEFAULT 'profile_1'")
            except Exception:
                pass
            conn.commit()
    except Exception as e:
        st.error(f"Error initializing DB schema: {e}")


# ── Sidebar Account Selector ──
st.sidebar.title("👤 Account Selector")
selected_profile = st.sidebar.selectbox(
    "Active Profile Account",
    ["profile_1", "profile_2"],
    format_func=lambda x: "👤 Profile 1 (Default)" if x == "profile_1" else "👤 Profile 2 (Secondary)",
)
st.sidebar.caption("All settings are managed via `profiles/<profile>/ .env` files.")

# ── Title & Navigation Tabs ──
st.title("🎯 Naukri Profile Refresh & Performance Analytics")
st.caption(f"Currently viewing data for: **{selected_profile.upper()}**")

tab_analytics, tab_stepper = st.tabs(
    ["📊 Recruiter Analytics", "🚀 Live Execution Stepper"]
)

# ==============================================================================
# TAB 1: 📊 RECRUITER ANALYTICS
# ==============================================================================
with tab_analytics:
    st.header(f"📊 Recruiter Search Visibility ({selected_profile.upper()})")

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
            # Query snapshots filtered by profile_id
            if db_type == "postgres":
                query_snap = "SELECT * FROM performance_snapshots WHERE profile_id = %s OR (profile_id IS NULL AND %s = 'profile_1') ORDER BY timestamp ASC"
                df_snapshots = pd.read_sql_query(query_snap, conn, params=(selected_profile, selected_profile))
            else:
                query_snap = "SELECT * FROM performance_snapshots WHERE profile_id = ? OR (profile_id IS NULL AND ? = 'profile_1') ORDER BY timestamp ASC"
                df_snapshots = pd.read_sql_query(query_snap, conn, params=(selected_profile, selected_profile))

            if df_snapshots.empty:
                st.info(f"ℹ️ No analytics recorded for **{selected_profile}** yet. Trigger a run in the **🚀 Live Execution Stepper** tab to populate data.")
            else:
                snapshot_ids = tuple(df_snapshots["id"].tolist())
                ids_str = ",".join(str(i) for i in snapshot_ids)

                df_breakdowns = pd.read_sql_query(
                    f"SELECT b.*, s.timestamp FROM action_breakdowns b JOIN performance_snapshots s ON b.snapshot_id = s.id WHERE s.id IN ({ids_str}) ORDER BY s.timestamp ASC",
                    conn,
                )
                df_keywords = pd.read_sql_query(
                    f"SELECT k.*, s.timestamp FROM top_keywords k JOIN performance_snapshots s ON k.snapshot_id = s.id WHERE s.id IN ({ids_str}) ORDER BY k.appearance_count DESC",
                    conn,
                )
                df_skills = pd.read_sql_query(
                    f"SELECT sk.*, s.timestamp FROM trending_skills sk JOIN performance_snapshots s ON sk.snapshot_id = s.id WHERE s.id IN ({ids_str}) ORDER BY sk.search_count_num DESC",
                    conn,
                )
                df_activities = pd.read_sql_query(
                    f"SELECT a.*, s.timestamp as snapshot_time FROM recruiter_activities a JOIN performance_snapshots s ON a.snapshot_id = s.id WHERE s.id IN ({ids_str}) ORDER BY a.id DESC",
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
                        title=f"90-Day Rolling Recruiter Actions ({selected_profile})",
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
# TAB 2: 🚀 LIVE PROFILE REFRESH STEPPER
# ==============================================================================
with tab_stepper:
    st.header(f"🚀 Live Execution Stepper — {selected_profile.upper()}")
    st.caption(f"Trigger an on-demand profile refresh for **{selected_profile}** with real-time visual step tracking and streaming logs.")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        run_full = st.button(f"🚀 Run Profile Refresh for {selected_profile.upper()}", type="primary", use_container_width=True)
    with col_b2:
        run_dry = st.button(f"🧪 Run Dry Run for {selected_profile.upper()}", use_container_width=True)

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
        cmd = ["python", "-m", "src.main", "--profile", selected_profile, "--no-jitter"]
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

                terminal_placeholder.markdown(
                    f'<div class="terminal-box">{"<br/>".join(log_lines[-20:])}</div>',
                    unsafe_allow_html=True,
                )

            process.wait()

            for s in steps:
                if s["status"] == "active":
                    s["status"] = "completed"
            render_stepper(steps)

            if process.returncode == 0:
                st.balloons()
                st.success(f"🎉 Execution for {selected_profile.upper()} finished successfully!")
            else:
                st.error(f"❌ Execution for {selected_profile.upper()} completed with warnings/errors.")

        except Exception as e:
            st.error(f"Error running subprocess: {e}")
