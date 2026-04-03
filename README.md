# 🚂 Train Punctuality Service

Predicts Indian Railways train arrival/departure times with confidence scores based on historical data.

## Architecture

```
GitHub Actions (cron)  →  Turso (cloud SQLite)  ←  Render.com (FastAPI)
   Playwright scraper        shared database          API server
   every 30 min                5GB free                750 hrs/mo free
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
# Install Turso CLI
curl -sSfL https://get.tur.so/install.sh | bash
turso auth login
turso db create train-punctuality
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

### 5. Deploy
- **API**: Push to GitHub → connect to Render.com → set env vars
- **Collector**: GitHub Actions runs automatically on push (set `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` as repo secrets)

## Running Tests
```bash
pip install -r requirements-collector.txt pytest
python -m pytest tests/ -v
```

## Cost: $0
All infrastructure is free tier — no credit card required.
