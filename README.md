# 🚂 Train Punctuality Service

Predicts Indian Railways train arrival/departure times with confidence scores based on historical data.

## Live

- **API**: https://train-punctuality-service.onrender.com
- **Database**: Turso (cloud SQLite, Mumbai region)
- **Collector**: Oracle Cloud VM (Hyderabad), cron every 30 min

## Architecture

```
Oracle VM (India)  →  Turso (cloud SQLite)  ←  Render.com (FastAPI)
  Playwright scraper      shared database         API server
  cron every 30 min        5GB free               750 hrs/mo free
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/trains/{trainNo}/predict?date=` | Predicted times at all stations |
| `GET /api/v1/trains/{trainNo}/stations/{stn}/history?from=&to=` | Historical delay data |
| `GET /api/v1/trains/{trainNo}/reliability?period=90d` | Reliability score 0-100 |
| `GET /api/v1/stations/{stn}/board?date=` | Station arrival/departure board |
| `GET /api/v1/health` | Service health check |

## Setup

### 1. Create Turso Database
```bash
curl -sSfL https://get.tur.so/install.sh | bash
turso auth login
turso db create train-punctuality --region ap-south-1
turso db tokens create train-punctuality
```

### 2. Set Environment Variables
```bash
cp .env.example .env
# Fill in TURSO_DATABASE_URL and TURSO_AUTH_TOKEN
```

### 3. Initialize DB & Seed Trains
```bash
pip install -r requirements-collector.txt
python -m scripts.seed_data --popular
```

### 4. Run Locally
```bash
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8080
```

## Deployment

### API (Render.com)
- Connect GitHub repo → Render.com
- Build: `pip install -r requirements.txt`
- Start: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
- Env vars: `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`

### Collector (Oracle Cloud VM)
The collector runs on an Always Free Oracle Cloud VM in India (required — NTES blocks non-Indian IPs).

**VM specs**: 1 OCPU, 503MB RAM + 2.5GB swap, Oracle Linux 9.7

**What's installed**:
- Python 3.9 + pip (system)
- Playwright + Chromium headless shell
- Chromium system libs (installed manually via rpm2cpio — yum/dnf OOMs on 503MB)

**Cron jobs** (IST = UTC+5:30):
| Schedule | Job |
|----------|-----|
| Every 30 min, midnight–6:30 PM IST | `python3 -m src.collector.daily_collector --all` |
| Daily 7 PM IST | Log rotation (keeps 7 days, rotates at 1MB) |

**Health check from your Mac**:
```bash
ssh -i ~/Downloads/ssh-key-2026-04-03.key opc@92.4.90.157 "bash /home/opc/train-punctuality-service/scripts/health_check.sh"
```

**Tail logs**:
```bash
ssh -i ~/Downloads/ssh-key-2026-04-03.key opc@92.4.90.157 "tail -20 /home/opc/collector.log"
```

**VM SSH**:
```bash
ssh -i ~/Downloads/ssh-key-2026-04-03.key opc@92.4.90.157
```

## Running Tests
```bash
pip install -r requirements-collector.txt pytest
python -m pytest tests/ -v
```

## Cost: $0
All infrastructure is free tier — no credit card charges.

| Component | Service | Free Tier |
|-----------|---------|-----------|
| Database | Turso | 5GB storage, 500M reads/mo |
| API | Render.com | 750 hrs/mo, sleeps after 15min idle |
| Collector | Oracle Cloud VM | Always Free (1 OCPU, 1GB RAM) |
