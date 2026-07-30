# 🎯 Naukri.com Profile Refresh Automation & Analytics Dashboard

> **Keep your profile at the top of recruiter searches — automatically. Track recruiter search visibility with PostgreSQL & Streamlit.**

This tool automates daily profile updates on Naukri.com using Playwright browser automation with human-like UI navigation, mouse movement, and scrolling. It parses your **Naukri Performance Analytics**, sends instant reports to Telegram, persists time-series data to **PostgreSQL**, and provides an interactive **Streamlit Dashboard** to visualize recruiter search trends over time.

---

## 🧠 Why This Works

Naukri.com's algorithm heavily weights **profile recency**. Recruiters filter by "Last Active" when searching candidates on **Resdex**. This automation:

| Action | Recruiter Impact |
|--------|-----------------|
| **Resume re-upload** | Strongest freshness signal — bumps "Last Updated" timestamp |
| **Headline rotation** | Matches different recruiter keyword searches |
| **Skills toggle** | Triggers "profile modified" event |
| **Summary touch** | Additional freshness signal (invisible changes) |
| **Performance parsing** | Captures 90-day recruiter views, downloads, search keywords, and trending skills |

---

## 🚀 Quick Start

### 1. Clone & Configure

```bash
# Copy the environment template
cp .env.example .env

# Edit with your Naukri credentials
nano .env   # or use any editor
```

**Required settings in `.env`:**
```env
NAUKRI_EMAIL=your_email@example.com
NAUKRI_PASSWORD=your_password
```

### 2. Add Your Resume

```bash
# Place your resume PDF in the resumes/ directory
cp ~/path/to/your_resume.pdf resumes/Surinder_Singh_Senior_Mobile_Engineer_Resume.pdf
```

### 3. Build & Launch (Docker Containers + Postgres + Streamlit Dashboard)

```bash
# Build and start all services in background
docker compose up -d --build

# Check status of containers
docker compose ps

# Watch application logs
docker compose logs -f naukri-updater
```

---

## 📊 Streamlit Analytics Dashboard

View interactive Plotly charts of your recruiter search appearances, top search keywords, and skill demand trends:

- **URL**: `http://localhost:8501`
- **Features**:
  - 📈 90-Day Recruiter Actions Trend line chart
  - 🔢 Latest Action Breakdown (Profile views, Contact views, Resume downloads, NVites)
  - 🔑 Top Keywords Recruiters Typed to Find You
  - ⚡ High Demand Relevant Skills in the Market
  - 💼 Recent Recruiter Activity Feed

```bash
# Run Streamlit locally outside Docker (optional):
source venv/bin/activate
streamlit run dashboard.py
```

---

## 🧪 Testing & Verification Guide

### 1. Dry Run Verification (Login Test Only — No Profile Changes)

#### Local Run (Visible Browser):
```bash
./scripts/run_local.sh --dry-run
```

#### Docker Container Run:
```bash
docker compose exec naukri-updater python -m src.main --dry-run
```

---

### 2. Full Execution Run (Real Profile Refresh + Analytics + Telegram)

#### Local Run (Visible Browser):
```bash
./scripts/run_local.sh
```

#### Docker Container Run:
```bash
docker compose exec naukri-updater python -m src.main
```

---

### 3. Automated PostgreSQL Database Verification

Verify stored analytics snapshots directly inside the PostgreSQL container:

```bash
# Check recorded performance snapshots
docker compose exec postgres psql -U naukri_user -d naukri_analytics -c "SELECT id, timestamp, total_actions, weekly_trend_pct, trend_direction FROM performance_snapshots;"

# Check latest action breakdown metrics
docker compose exec postgres psql -U naukri_user -d naukri_analytics -c "SELECT metric_name, metric_count FROM action_breakdowns ORDER BY id DESC LIMIT 10;"

# Check top recruiter search keywords
docker compose exec postgres psql -U naukri_user -d naukri_analytics -c "SELECT keyword, appearance_count FROM top_keywords ORDER BY id DESC LIMIT 10;"

# Check trending skills
docker compose exec postgres psql -U naukri_user -d naukri_analytics -c "SELECT skill_name, search_count_str FROM trending_skills ORDER BY id DESC LIMIT 10;"

# Check recent recruiter activity log
docker compose exec postgres psql -U naukri_user -d naukri_analytics -c "SELECT company_name, action_type, time_ago_str FROM recruiter_activities ORDER BY id DESC LIMIT 10;"
```

---

### 4. Data Persistence Test (Proving Data Survives Container Removal)

Verify that PostgreSQL data is safely stored outside the container in `./postgres_data`:

```bash
# 1. Stop and remove all containers
docker compose down

# 2. Re-create and start containers
docker compose up -d

# 3. Query PostgreSQL — all historical records will still be intact!
docker compose exec postgres psql -U naukri_user -d naukri_analytics -c "SELECT COUNT(*) AS total_historical_snapshots FROM performance_snapshots;"
```

---

## ⚙️ Configuration Reference

All settings are in `.env`. Key options:

| Variable | Default | Description |
|----------|---------|-------------|
| `NAUKRI_EMAIL` | *(required)* | Your Naukri login email |
| `NAUKRI_PASSWORD` | *(required)* | Your Naukri password |
| `RESUME_PATH` | `/app/resumes/...` | Path to resume PDF file |
| `TARGET_ROLE` | `Senior Software Engineer` | Your target position |
| `ENABLE_HEADLINE_ROTATION` | `true` | Set to `false` or leave `HEADLINES` blank to skip |
| `HEADLINES` | Multiple variations | Comma-separated headline rotations |
| `ENABLE_SKILLS_UPDATE` | `true` | Set to `false` or leave `KEY_SKILLS` blank to skip |
| `KEY_SKILLS` | Common tech skills | Comma-separated skills list |
| `CRON_SCHEDULE` | `0 8 * * *` | Cron expression (default: 8 AM IST daily) |
| `TELEGRAM_BOT_TOKEN` | *(optional)* | Telegram bot token for alerts |
| `TELEGRAM_CHAT_ID` | *(optional)* | Your Telegram chat ID |
| `ENABLE_DB_STORAGE` | `true` | Save analytics to PostgreSQL / SQLite |
| `POSTGRES_DB` | `naukri_analytics` | PostgreSQL database name |
| `POSTGRES_USER` | `naukri_user` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `naukri_secure_password_123` | PostgreSQL password |
| `POSTGRES_HOST` | `postgres` | Host (`postgres` for Docker, `localhost` for local) |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `HEADLESS` | `true` | Run browser headlessly (`false` for visible UI) |
| `HUMAN_DELAY_RANGE` | `2,5` | Random delay range (seconds) |

---

## 📱 Telegram Notifications

Get instant alerts when your profile is updated and receive parsed performance metrics:

1. **Create a bot**: Message [@BotFather](https://t.me/botfather) on Telegram → `/newbot`
2. **Get your Chat ID**: Message [@userinfobot](https://t.me/userinfobot) → it replies with your ID
3. **Start Conversation**: Send `/start` or any text message to your bot so it can reply.
4. **Add to `.env`**:
   ```env
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   TELEGRAM_CHAT_ID=987654321
   ```

---

## 🛠️ Docker & Operations Reference

```bash
# Start all containers in background
docker compose up -d

# Stop all containers
docker compose stop

# Restart containers
docker compose restart

# View logs
docker compose logs -f naukri-updater

# Rebuild after code changes
docker compose up -d --build

# Stop and remove containers (data remains safe in ./postgres_data)
docker compose down
```

---

## 📁 Project Structure

```
naukri_profile_update/
├── Dockerfile                  # Container build
├── docker-compose.yml          # Services: naukri-updater, postgres, dashboard
├── dashboard.py                # Streamlit interactive analytics dashboard
├── .env.example                # Config template
├── .env                        # Credentials & DB settings (gitignored)
├── requirements.txt            # Python deps (Playwright, psycopg2, Streamlit, Plotly)
├── postgres_data/              # Host volume directory for persistent Postgres storage
├── src/
│   ├── main.py                 # Main entry point & orchestrator
│   ├── config.py               # Config loader & feature flags
│   ├── browser.py              # Playwright browser manager with anti-detection
│   ├── login.py                # Login handler & session persistence
│   ├── resume_uploader.py      # Human UI resume upload (scroll & button click)
│   ├── headline_rotator.py     # Headline keyword rotator
│   ├── profile_updater.py      # Skills & summary updater
│   ├── performance_parser.py   # Performance analytics page parser
│   ├── db.py                   # PostgreSQL layer with local SQLite fallback
│   ├── notifier.py             # Telegram alerts (status + analytics summary)
│   └── utils.py                # Human delays & curved mouse movement simulation
├── resumes/                    # Resume PDF files directory
├── logs/                       # Persistent application logs & SQLite fallback DB
└── scripts/
    ├── run_local.sh            # Local visible test runner
    ├── entrypoint.sh           # Container entrypoint & cron setup
    └── healthcheck.sh          # Container health check
```
