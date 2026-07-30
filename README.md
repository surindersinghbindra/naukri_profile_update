# 🎯 Naukri.com Profile Refresh Automation & Analytics Dashboard

> **Keep your profile at the top of recruiter searches automatically. Manage multiple accounts with PostgreSQL time-series storage & an interactive Streamlit Dashboard.**

This tool automates daily profile updates on Naukri.com using Playwright browser automation with human-like UI navigation, curved mouse movements, and scrolling. It supports **Multi-Profile Management** (running independent accounts cleanly), parses **Naukri Performance Analytics**, sends instant reports to Telegram, persists time-series data to **PostgreSQL**, and provides an interactive **Streamlit Dashboard** to visualize recruiter search trends over time.

---

## 🌟 Key Features

- **👥 Multi-Profile Support (`profile_1` & `profile_2`)**: Manage multiple independent Naukri accounts with isolated browser sessions and cookies (zero state leakage).
- **🛡️ Anti-Bot Evasion**: Playwright Chromium executes Naukri’s native client-side JS to compute dynamic security tokens (`nkparam`) and headers automatically.
- **🖱️ Human-Like UI Interaction**: Smooth curved Bezier mouse paths, random wheel scrolling, left navigation menu clicking, and native browser OS file chooser interception.
- **🛡️ Safe Profile-Toggling Mode (`ENABLE_RESUME_UPLOAD=false`)**: Rotates headline keywords, reorders key skills, and touches summary timestamps without re-uploading PDF files (0% file upload risk / 100% Resdex rank boost).
- **📄 Full Refresh Mode (`ENABLE_RESUME_UPLOAD=true`)**: Re-uploads your CV PDF file using real DOM button clicks and file chooser interception.
- **🎲 Schedule Start Delay Jitter (`SCHEDULE_JITTER_*`)**: Adds randomized min/max minutes & seconds start delays so scheduled cron executions do not run at the exact same second every day.
- **📊 PostgreSQL Time-Series Storage**: Saves recruiter actions, metric breakdowns, top recruiter search keywords, market skill demand, and recruiter activity feeds tagged by `profile_id`.
- **🎛️ Interactive Streamlit Dashboard (`http://localhost:8501`)**:
  - 👤 **Sidebar Account Switcher**: Easily toggle between `Profile 1` and `Profile 2`.
  - 📊 **Recruiter Analytics Tab**: Plotly line charts, action breakdown pie charts, top keyword bar charts, and recruiter activity feed.
  - 🚀 **Live Execution Stepper Tab**: Step-by-step progress cards featuring glowing **pulsing beat animations** for active steps, green checkmarks for completed steps, on-demand run triggers (`🚀 Run Profile Refresh Now` / `🧪 Run Dry Run`), and real-time streaming terminal log console.
- **📱 Telegram Notifications**: Instant status alerts and rich performance metric reports sent directly to your phone.

---

## 🏗️ Architecture & Directory Structure

```mermaid
graph TD
    subgraph File-Based Configurations
        F1[profiles/profile_1/.env] --> P1[Profile 1 Config]
        F2[profiles/profile_2/.env] --> P2[Profile 2 Config]
    end

    subgraph Docker Multi-Container Architecture
        P1 --> Service1[updater-profile1]
        P2 --> Service2[updater-profile2]
        
        Service1 -->|profile_id = 'profile_1'| DB[(PostgreSQL Database)]
        Service2 -->|profile_id = 'profile_2'| DB
        
        Service1 --> S1[(profiles/profile_1/session_storage)]
        Service2 --> S2[(profiles/profile_2/session_storage)]
    end

    subgraph Streamlit Dashboard :8501
        Dropdown[👤 Sidebar Account Selector: Profile 1 | Profile 2] --> DashboardApp[dashboard.py]
        DashboardApp -->|Query metrics by profile_id| DB
    end

    DB -->|Host Volume Persistence| Vol[./postgres_data]
```

### 📂 Directory Layout
```text
naukri_profile_update/
├── Dockerfile                  # Container build
├── docker-compose.yml          # Services: updater-profile1, updater-profile2, postgres, dashboard
├── dashboard.py                # Streamlit analytics dashboard & live stepper
├── requirements.txt            # Python dependencies (Playwright, psycopg, Streamlit, Plotly)
├── postgres_data/              # Host volume directory for persistent Postgres storage
├── profiles/
│   ├── profile_1/
│   │   ├── .env                # Account 1 configuration & credentials
│   │   ├── session_storage/    # Isolated session cookies for Account 1
│   │   └── resumes/            # Account 1 resume PDF
│   └── profile_2/
│       ├── .env                # Account 2 configuration & credentials
│       ├── session_storage/    # Isolated session cookies for Account 2
│       └── resumes/            # Account 2 resume PDF
├── src/
│   ├── main.py                 # CLI entry point orchestrator (--profile, --dry-run, --no-jitter)
│   ├── config.py               # Config loader with profile support
│   ├── browser.py              # Playwright browser manager with stealth anti-detection
│   ├── login.py                # Login handler & session persistence
│   ├── resume_uploader.py      # Human UI resume upload (scroll & button click)
│   ├── headline_rotator.py     # Headline keyword rotator
│   ├── profile_updater.py      # Skills & summary updater
│   ├── performance_parser.py   # Performance analytics page parser
│   ├── db.py                   # PostgreSQL layer with profile_id tagging & SQLite fallback
│   ├── notifier.py             # Telegram alerts (status + analytics summary)
│   └── utils.py                # Human delays & curved mouse movement simulation
├── logs/                       # Application logs & SQLite fallback DB
└── scripts/
    ├── run_local.sh            # Local visible test runner
    ├── entrypoint.sh           # Container entrypoint & cron setup
    └── healthcheck.sh          # Container health check
```

---

## 🚀 Quick Start Guide

### 1. Configure Profile Settings

Configure `.env` files for **Profile 1** and **Profile 2**:

```bash
# Edit Account 1 settings
nano profiles/profile_1/.env

# Edit Account 2 settings
nano profiles/profile_2/.env
```

**Required parameters in `.env`:**
```env
NAUKRI_EMAIL=your_email@example.com
NAUKRI_PASSWORD=your_password
```

### 2. Add Resume PDF Files

```bash
# Copy Account 1 resume
cp ~/path/to/resume1.pdf profiles/profile_1/resumes/Surinder_Singh_Resume.pdf

# Copy Account 2 resume
cp ~/path/to/resume2.pdf profiles/profile_2/resumes/Surinder_Singh_Resume.pdf
```

### 3. Launch Docker Services (Postgres + Updaters + Streamlit Dashboard)

```bash
# Build and start all containers in background
docker compose up -d --build

# Check status of running containers
docker compose ps

# Watch logs
docker compose logs -f updater-profile1
```

---

## 🎛️ Streamlit Dashboard & Control Hub

Open **`http://localhost:8501`** in your browser:

- 👤 **Sidebar Account Switcher**: Select between `Profile 1` and `Profile 2`.
- 📊 **Recruiter Analytics Tab**:
  - 📈 90-Day Recruiter Actions Trend line chart (Plotly)
  - 🔢 Action Breakdown pie chart (Profile views, Contact views, Resume downloads, NVites)
  - 🔑 Top Keywords Recruiters Typed to Find You (Horizontal bar chart)
  - ⚡ High Demand Relevant Skills in the Market
  - 💼 Recent Recruiter Activity Feed table
- 🚀 **Live Execution Stepper Tab**:
  - Step-by-step progress cards featuring glowing **pulsing beat animations** (`pulse-blue`) for active steps and green checkmarks (`✅`) for completed steps.
  - Interactive terminal console streaming log output line-by-line in real time.
  - On-demand run triggers (`🚀 Run Profile Refresh Now` / `🧪 Run Dry Run`).

---

## 🧪 Testing & Verification Guide

### 1. CLI Execution Commands (Local or Inside Container)

#### Dry Run Test (Login verification only — no profile modifications):
```bash
# Dry run Profile 1
python -m src.main --profile profile_1 --dry-run

# Dry run Profile 2
python -m src.main --profile profile_2 --dry-run
```

#### Full Execution Run:
```bash
# Full run Profile 1 (skip schedule jitter)
python -m src.main --profile profile_1 --no-jitter

# Full run Profile 2 (skip schedule jitter)
python -m src.main --profile profile_2 --no-jitter
```

#### Local Runner Script (Visible Browser):
```bash
./scripts/run_local.sh --dry-run
```

---

### 2. Automated PostgreSQL Database Verification

Verify stored analytics snapshots directly inside the PostgreSQL container:

```bash
# Query snapshots for Profile 1
docker compose exec postgres psql -U naukri_user -d naukri_analytics -c "SELECT id, profile_id, timestamp, total_actions, weekly_trend_pct, trend_direction FROM performance_snapshots WHERE profile_id = 'profile_1';"

# Query snapshots for Profile 2
docker compose exec postgres psql -U naukri_user -d naukri_analytics -c "SELECT id, profile_id, timestamp, total_actions, weekly_trend_pct, trend_direction FROM performance_snapshots WHERE profile_id = 'profile_2';"

# Check action breakdown metrics
docker compose exec postgres psql -U naukri_user -d naukri_analytics -c "SELECT s.profile_id, b.metric_name, b.metric_count FROM action_breakdowns b JOIN performance_snapshots s ON b.snapshot_id = s.id ORDER BY b.id DESC LIMIT 10;"

# Check top search keywords
docker compose exec postgres psql -U naukri_user -d naukri_analytics -c "SELECT s.profile_id, k.keyword, k.appearance_count FROM top_keywords k JOIN performance_snapshots s ON k.snapshot_id = s.id ORDER BY k.id DESC LIMIT 10;"
```

---

### 3. Data Persistence Test (Proving Data Survives Container Removal)

Verify that PostgreSQL data is safely stored outside the container in `./postgres_data`:

```bash
# 1. Stop and remove containers
docker compose down

# 2. Re-create and start containers
docker compose up -d

# 3. Query PostgreSQL — all historical records will still be intact!
docker compose exec postgres psql -U naukri_user -d naukri_analytics -c "SELECT profile_id, COUNT(*) AS total_historical_snapshots FROM performance_snapshots GROUP BY profile_id;"
```

---

## ⚙️ Configuration Reference (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NAUKRI_EMAIL` | *(required)* | Your Naukri login email |
| `NAUKRI_PASSWORD` | *(required)* | Your Naukri password |
| `ENABLE_RESUME_UPLOAD` | `true` | Set to `false` for **Safe Profile-Toggling Mode** (no file upload risk) |
| `RESUME_PATH` | `profiles/<profile>/resumes/resume.pdf` | Path to resume PDF file |
| `TARGET_ROLE` | `Senior Software Engineer` | Your target position |
| `ENABLE_HEADLINE_ROTATION` | `true` | Enable/disable headline variation updates |
| `HEADLINES` | Comma-separated list | Comma-separated headline rotation variations |
| `ENABLE_SKILLS_UPDATE` | `true` | Enable/disable key skills toggle |
| `KEY_SKILLS` | Comma-separated list | Comma-separated skills list to rotate/reorder |
| `CRON_SCHEDULE` | `0 8 * * *` | Cron expression (default: 8:00 AM IST daily) |
| `SCHEDULE_JITTER_MIN_MINUTES` | `0` | Min random minutes delay to prevent fixed-time bot detection |
| `SCHEDULE_JITTER_MAX_MINUTES` | `15` | Max random minutes delay |
| `SCHEDULE_JITTER_MIN_SECONDS` | `0` | Min random seconds delay |
| `SCHEDULE_JITTER_MAX_SECONDS` | `59` | Max random seconds delay |
| `TELEGRAM_BOT_TOKEN` | *(optional)* | Telegram bot token for phone alerts |
| `TELEGRAM_CHAT_ID` | *(optional)* | Your Telegram chat ID |
| `ENABLE_DB_STORAGE` | `true` | Save analytics to PostgreSQL / SQLite |
| `POSTGRES_DB` | `naukri_analytics` | PostgreSQL database name |
| `POSTGRES_USER` | `naukri_user` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `naukri_secure_password_123` | PostgreSQL password |
| `POSTGRES_HOST` | `postgres` | Host (`postgres` for Docker, `localhost` for local) |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `HEADLESS` | `true` | Run browser headlessly (`false` for visible UI) |
| `HUMAN_DELAY_RANGE` | `2,5` | Random delay range in seconds |

---

## 📱 Telegram Notifications Setup

1. **Create a bot**: Message [@BotFather](https://t.me/botfather) on Telegram → `/newbot`
2. **Get your Chat ID**: Message [@userinfobot](https://t.me/userinfobot) → it replies with your ID
3. **Start Conversation**: Send `/start` or any text message to your bot so it can reply.
4. **Add to `.env`**:
   ```env
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   TELEGRAM_CHAT_ID=987654321
   ```

---

---

## 🤖 GitHub Actions Automated Deployment via Tailscale

Automated CI/CD deployment workflow is configured in `.github/workflows/deploy.yml`:

Pushes to `main` or `master` branch automatically connect to your home server over your secure **Tailscale Network**, pull the latest code, execute `docker compose down`, rebuild images, and restart services cleanly.

### 🔐 Required GitHub Repository Secrets
Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret Name | Value Example | Description |
|-------------|---------------|-------------|
| `TAILSCALE_AUTHKEY` | `tskey-auth-k123456789...` | Ephemeral or reusable key from Tailscale Admin Console |
| `TAILSCALE_SERVER_IP` | `100.110.120.130` | Your home server's Tailscale IP address |
| `SERVER_USER` | `surindersingh` | SSH username on your home server |
| `SSH_PRIVATE_KEY` | `-----BEGIN OPENSSH PRIVATE KEY-----...` | Your SSH private key |
| `SERVER_PROJECT_PATH` | `~/naukri_profile_update` | Path to project folder on home server |


