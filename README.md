# 🚂 Train Punctuality Service

Predicts Indian Railways train arrival/departure times with confidence scores based on historical data.

## Live

- **API**: https://train-punctuality-service.onrender.com
- **Database**: Turso (cloud SQLite, Mumbai region)
- **Collector**: GitHub Actions (cron) → SOCKS proxy through Oracle Cloud VM (Indian IP)

## Architecture

```
GitHub Actions (cron)  ──SSH tunnel──▶  Oracle VM (India)  ──▶  NTES
  Playwright + Python       SOCKS5 proxy on :1080              Indian Railways
  every 30 min              routes traffic via Indian IP        live train data
       │
       ▼
  Turso (cloud SQLite)  ◀──  Render.com (FastAPI)
    shared database            API server
    5GB free                   750 hrs/mo free
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

### Collector (GitHub Actions + Oracle VM SOCKS Proxy)
Data collection runs on **GitHub Actions** (cron every 30 min). NTES blocks non-Indian IPs, so
Playwright traffic is routed through an **Oracle Cloud VM in India** via an SSH SOCKS5 tunnel.

**How it works**:
1. GitHub Actions starts, opens SSH tunnel to Oracle VM (`ssh -D 1080`)
2. Playwright launches Chromium with `PROXY_SERVER=socks5://localhost:1080`
3. All browser traffic exits through the Oracle VM's Indian IP
4. Scraped data is written directly to Turso (cloud SQLite)

**GitHub Secrets required**:
| Secret | Description |
|--------|-------------|
| `ORACLE_SSH_KEY` | SSH private key for `opc@<VM_IP>` |
| `ORACLE_VM_IP` | Oracle VM public IP (Hyderabad region) |
| `TURSO_DATABASE_URL` | Turso database URL |
| `TURSO_AUTH_TOKEN` | Turso auth token |

**Oracle VM role**: SOCKS proxy only — no Python, no Playwright, no cron on the VM itself.

**VM SSH** (for debugging proxy):
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
| Collector | GitHub Actions + Oracle VM | GH Actions: 2000 min/mo free; Oracle VM: Always Free |
