# 🚂 Indian Railways Train Punctuality Prediction Service

## Project Plan & Complete Reference

> **Created:** 2026-04-02
> **Status:** Phase 1 — MVP Development
> **Language:** Python 3.11+
> **Cost:** $0 (fully free infrastructure)

---

## Table of Contents

1. [Vision & Goal](#1-vision--goal)
2. [Use Cases (All Phases)](#2-use-cases-all-phases)
3. [Edge Cases & Data Complexities](#3-edge-cases--data-complexities)
4. [Tech Stack](#4-tech-stack)
5. [Data Sources (All Free)](#5-data-sources-all-free)
6. [Data Model & Schema](#6-data-model--schema)
7. [API Design](#7-api-design)
8. [Data Collection Strategy](#8-data-collection-strategy)
9. [Prediction Engine Design](#9-prediction-engine-design)
10. [Phase 1 — MVP Scope & Plan](#10-phase-1--mvp-scope--plan)
11. [Phase 2 & 3 — Future Roadmap](#11-phase-2--3--future-roadmap)
12. [Infrastructure & Hosting](#12-infrastructure--hosting)
13. [Open Questions & Risks](#13-open-questions--risks)

---

## 1. Vision & Goal

Build a **fully autonomous, 100% free** service that:
- Collects actual arrival/departure times for every Indian Railways train every day
- Stores historical punctuality data
- **Predicts future arrival/departure times** at any station for any train with a **confidence percentage**
- Enables users to assess train reliability for booking onward journeys or scheduling plans

### Core Value Proposition
> "Train 12301 Rajdhani is predicted to arrive at Kanpur at 22:47 ± 12 min (87% confidence).
> Based on history, this train is late >30 min only 8% of the time at this station."

---

## 2. Use Cases (All Phases)

### Phase 1 — MVP (Core)

| ID | Use Case | Description | API Endpoint |
|----|----------|-------------|--------------|
| **UC-1** | Train ETA Prediction | Predicted arrival/departure at all stations with confidence % | `GET /api/v1/trains/{trainNo}/predict?date=` |
| **UC-2** | Historical Time Graph | Actual times at a station over time (weekly/monthly/quarterly/yearly) | `GET /api/v1/trains/{trainNo}/stations/{stnCode}/history?period=&from=&to=` |
| **UC-3** | Train Reliability Score | Single 0-100 score + stats (avg delay, on-time %, worst stations) | `GET /api/v1/trains/{trainNo}/reliability?period=` |
| **UC-9** | Station Live Board | All trains today at a station with predicted actual times | `GET /api/v1/stations/{stnCode}/board?date=` |

### Phase 2 — Intelligence

| ID | Use Case | Description | API Endpoint |
|----|----------|-------------|--------------|
| **UC-4** | Station Delay Heatmap | Avg delay introduced per station, worst trains, peak hours | `GET /api/v1/stations/{stnCode}/delay-stats?period=` |
| **UC-5** | Onward Journey Planner | Safe connecting trains with miss-probability % (**killer feature**) | `GET /api/v1/connections/plan?arrivalTrain=&station=&date=&minBuffer=` |
| **UC-7** | Route Segment Analysis | Per-segment delay gain/loss analysis | `GET /api/v1/trains/{trainNo}/segments/analysis?period=` |
| **UC-8** | Train Comparison | Side-by-side punctuality comparison of 2+ trains | `GET /api/v1/compare?trains=12301,12259&period=` |

### Phase 3 — Engagement

| ID | Use Case | Description | API Endpoint |
|----|----------|-------------|--------------|
| **UC-6** | Delay Pattern Insights | Correlate delays with season, day-of-week, festivals, fog | `GET /api/v1/insights/delay-patterns?route=&season=` |
| **UC-10** | Delay Alerts | Subscribe to train — notify if predicted delay > threshold | `POST /api/v1/alerts/subscribe` |

---

## 3. Edge Cases & Data Complexities

### 3.1 Train Running Frequency

| Pattern | Example | Handling |
|---------|---------|----------|
| **Daily** | 12301 Howrah Rajdhani | Collect every day |
| **Specific days** | 12953 Aug Kranti (Mon/Wed/Sat) | Store `run_days` bitmap, skip collection on non-running days |
| **Bi-weekly** | Some Garib Rath trains | Same as above — run_days = [Tue, Fri] |
| **Tri-weekly** | Many express trains | Same — check schedule before collecting |
| **Weekly (1 day)** | 12523 NJP-NDLS (Sat only) | Only collect on Saturdays |
| **Fortnightly** | Very rare services | Store as `frequency_type: FORTNIGHTLY` with specific dates |
| **Seasonal/Special** | Summer specials, Pooja specials, Kumbh specials | Temporary trains — detect from NTES, flag as `is_special: true` |
| **Festival specials** | Diwali/Holi/Christmas extras | Same as seasonal, flag `is_festival_special: true` |
| **One-time specials** | Inaugurals, PM specials | Collect but exclude from predictions |

### 3.2 Train Number Complexities

| Edge Case | Example | Handling |
|-----------|---------|----------|
| **Up/Down pairs** | 12301 (HWH→NDLS) / 12302 (NDLS→HWH) | Treat as separate trains, link via `pair_train_number` |
| **Number changes mid-route** | Some trains change number at a junction | Track as single journey, store `alternate_numbers[]` |
| **Temporary renumbering** | Diverted trains get suffixed numbers (e.g., 02301) | Map 02301 → 12301 with flag `is_diverted: true` |
| **0xxxx prefix** | Special trains always start with 0 | Flag `is_special: true`, prefix 0 indicates special/one-time |
| **Slip coaches** | Coach detaches at junction, continues with different train | Track as separate journey from the junction station |
| **Replaced by another train** | Train X cancelled, passengers shifted to train Y | Log cancellation event, don't confuse data |

### 3.3 Timing & Date Edge Cases

| Edge Case | Example | Handling |
|-----------|---------|----------|
| **Midnight crossover** | Arrives 23:50, departs 00:10 next day | Store absolute datetime (not just time), handle date rollover |
| **Multi-day journeys** | Kerala Express: 3 days (NDLS→TVC) | Each station has `day_number` (1, 2, or 3) relative to origin departure |
| **Same station, different times** | Train loops back through a station (rare) | Use `sequence_number` to differentiate first vs second stop |
| **Origin station** | No arrival time — only departure | `actual_arrival = null`, only track departure |
| **Destination station** | No departure time — only arrival | `actual_departure = null`, only track arrival |
| **Technical halt** | Train stops 1-2 min, passengers can't board | Flag `halt_type: TECHNICAL` — don't show in passenger-facing data |
| **Conditional/flag stop** | Stops only if passengers have booked | Flag `halt_type: CONDITIONAL` — may or may not have actual time |
| **Unscheduled stop** | Train stops at a station not in schedule | Log with `is_unscheduled: true` — don't include in predictions |
| **"On time" tolerance** | NTES shows "on time" if ≤5 min late | Record raw delay, treat "Right Time (RT)" as 0 delay, actual delay may be 0-5 min |
| **Rescheduled departure** | Origin departure pushed by 2 hours | Store `rescheduled_departure` separately, compute delay from ORIGINAL schedule |
| **No data available** | NTES doesn't update for some trains | Mark as `data_status: UNAVAILABLE`, don't fill with zeros |
| **IST only** | India doesn't observe DST | No timezone edge case — everything in IST (UTC+5:30) ✓ |

### 3.4 Route & Station Edge Cases

| Edge Case | Example | Handling |
|-----------|---------|----------|
| **Route diversion** | Track work → train rerouted via different stations | Flag `is_diverted: true`, store `diverted_route[]` separately |
| **Partial cancellation (origin side)** | Train starts from a station mid-route | Store `actual_origin` ≠ `scheduled_origin`, mark skipped stations as `CANCELLED` |
| **Partial cancellation (destination side)** | Train short-terminated early | Store `actual_destination`, mark remaining stations as `SHORT_TERMINATED` |
| **Full cancellation** | Entire train cancelled for the day | Store `run_status: CANCELLED` — important for reliability scoring |
| **Regulated/held** | Train held at a station by control | Shows as delay — no special handling needed, just larger delay value |
| **Junction divergence** | At Itarsi junction, train can go via 2 routes | Store actual route taken — affects which stations show data |
| **Station code changes** | Station renamed/recoded (rare) | Maintain `station_aliases[]` mapping table |
| **Phantom stations** | NTES shows stations that don't exist in master data | Skip with warning log, maintain `unknown_stations` list for review |
| **Multiple platforms** | Train scheduled on Pf 3, moved to Pf 7 | Store `platform_number` — useful for passenger info but doesn't affect predictions |

### 3.5 Seasonal & Environmental Patterns

| Factor | Period | Impact | Handling |
|--------|--------|--------|----------|
| **Fog season** | Dec 15 — Feb 15 (North India) | 2-8 hour delays, especially Delhi/UP/Bihar belt | Flag `is_fog_season: true`, separate prediction model for fog season |
| **Monsoon** | Jun — Sep | Flooding, landslides (especially Konkan, NE India) | Flag `is_monsoon_season: true`, track cancellation rate |
| **Summer** | Apr — Jun | Track buckling in extreme heat, some speed restrictions | Flag `is_summer: true` |
| **Festival rush** | Diwali, Holi, Chhath, Pongal, Christmas | Overcrowding → longer halts → cascading delays | Flag `is_festival_period: true` with festival name |
| **Exam season** | Mar — Jun | Extra trains, heavy north-south traffic | Flag `is_exam_season: true` |
| **Kumbh Mela** | Every 3/6/12 years | Massive specials, major diversions around Prayagraj | Flag `is_kumbh: true` |
| **Parliament sessions** | Budget week, etc. | Some trains get priority, Rajdhanis rarely delayed | Note in metadata |
| **Track maintenance blocks** | Announced in advance | Major diversions, systematic delays on specific routes | Detect from cancellation patterns |
| **Day of week** | Fri/Sun have heavier traffic | Weekend travel rush → more delays | Store `day_of_week` (already planned) |
| **Holiday Mondays** | Republic Day, Independence Day, Gandhi Jayanti | Mixed pattern — some trains less crowded, some more | Flag `is_public_holiday: true` |

### 3.6 Data Collection Edge Cases

| Edge Case | Handling |
|-----------|----------|
| **NTES down/unreachable** | Retry with exponential backoff (3 attempts), mark data as UNAVAILABLE |
| **NTES returns stale data** | Compare `last_updated` timestamp — skip if older than 30 min |
| **NTES rate limiting** | Throttle requests to 1 per second, rotate user-agents |
| **Partial NTES response** | Some stations have data, others don't — store what's available |
| **NTES format change** | Alert on parsing errors, switch to backup scraping logic |
| **Duplicate data** | Deduplicate by `(train_number, date, station_code, sequence)` composite key |
| **Train not yet started** | Status shows "Not Yet Started" — collect later in the day |
| **Journey completed** | All stations have actual times — no more collection needed |
| **Train running late by >24 hours** | Very rare but possible — ensure datetime arithmetic handles this |
| **MEMU/DEMU/Local trains** | NTES may not track these — skip and document as unsupported |
| **Goods/freight trains** | Not relevant — filter out by train number range |

### 3.7 Prediction Edge Cases

| Edge Case | Handling |
|-----------|----------|
| **New train (no history)** | Use average delay of similar train types on that route |
| **Train ran <10 times** | Low confidence score (cap at 40%), warn "insufficient data" |
| **Route recently changed** | Detect schedule changes, reset predictions for affected stations |
| **Seasonal shift** | Use season-weighted predictions (fog season model vs normal model) |
| **One-off extreme delay** | Outlier detection — exclude delays >6 hours from prediction model |
| **Cancelled days** | Don't count cancellations as "delay" — separate cancellation probability metric |
| **Cascading delays** | Train A delay causes Train B delay — track correlation for future UC-5 |

---

## 4. Tech Stack

| Component | Technology | Cost |
|-----------|------------|------|
| **Language** | Python 3.11+ | Free |
| **Web Scraping** | `httpx` (async) + `BeautifulSoup4` | Free |
| **JS-heavy pages** | `playwright` (headless Chromium) | Free |
| **Scheduling** | `APScheduler` (in-process) + GitHub Actions (cron backup) | Free |
| **Database** | SQLite (primary) + Parquet files (archival) | Free |
| **ML / Prediction** | `scikit-learn` + `Facebook Prophet` + `numpy` | Free |
| **API Server** | `FastAPI` + `Uvicorn` | Free |
| **Data Processing** | `pandas` + `numpy` | Free |
| **Hosting** | Render.com free tier (750 hrs/mo) OR Fly.io (3 free VMs) | Free |
| **CI/CD** | GitHub Actions (free for public repos) | Free |
| **Monitoring** | UptimeRobot (50 monitors free) | Free |
| **User-Agent Rotation** | `fake-useragent` | Free |
| **Charting (API response)** | JSON data + frontend renders (Chart.js/Recharts) | Free |

---

## 5. Data Sources (All Free)

### Primary Source: NTES (National Train Enquiry System)

**Base URL:** `https://enquiry.indianrail.gov.in/mntes/`

| Endpoint | Purpose | Data Returned |
|----------|---------|---------------|
| `q?opt=RunningTrain&trainNo={}&journeyDate={DD-MM-YYYY}` | Live running status | Actual times at each passed station, delay, platform |
| `q?opt=TrainSchedule&trainNo={}` | Static schedule | All stations, scheduled times, halt duration, distance |
| `q?opt=StationArrDep&stationCode={}&hours={}&trainType=ALL` | Station board | All trains at a station within N hours |
| `q?opt=TrainBetweenStn&fromStation={}&toStation={}&journeyDate={}` | Trains between stations | All trains between two stations on a date |

**Rate limits:** No official documentation. Estimated safe rate: **1 request/second**, rotate user-agents.

### Secondary Sources

| Source | URL | Data | Method |
|--------|-----|------|--------|
| **data.gov.in** | `data.gov.in/catalog/indian-railways` | Station master, historical datasets | REST API (free key) |
| **erail.in** | `erail.in` | Timetables, routes, coach position | Scrape |
| **RapidAPI** | Various | PNR, live status (500 req/day free) | REST API |
| **Indian Railways community datasets** | GitHub | Station codes, train lists, zone data | Download |

### One-Time Reference Data

| Dataset | Source | Records | Update Frequency |
|---------|--------|---------|------------------|
| Station master list | data.gov.in + NTES | ~8,000+ | Monthly refresh |
| Train list with schedules | NTES + erail.in | ~13,000+ | Monthly refresh |
| Train running days | NTES schedule endpoint | Per train | Monthly refresh |
| Zone/Division mapping | data.gov.in | 18 zones, 71 divisions | Yearly |
| Indian public holidays | Static list + detection | ~20/year | Yearly |
| Festival dates | Static list | ~15 major festivals/year | Yearly |
| Fog season dates | Fixed: Dec 15 — Feb 15 | Fixed | Never (hardcoded) |

---

## 6. Data Model & Schema

### SQLite Tables

```sql
-- Reference data (loaded once, refreshed monthly)

CREATE TABLE stations (
    station_code    TEXT PRIMARY KEY,        -- "NDLS"
    station_name    TEXT NOT NULL,           -- "New Delhi"
    zone            TEXT,                    -- "NR" (Northern Railway)
    division        TEXT,                    -- "Delhi"
    state           TEXT,                    -- "Delhi"
    latitude        REAL,
    longitude       REAL,
    station_category TEXT,                   -- "NSG-1", "A1", "A", "B"...
    num_platforms   INTEGER,
    aliases         TEXT,                    -- JSON array: ["DEL", "NDLI"]
    updated_at      TEXT NOT NULL            -- ISO datetime
);

CREATE TABLE trains (
    train_number    TEXT PRIMARY KEY,        -- "12301"
    train_name      TEXT NOT NULL,           -- "Howrah Rajdhani"
    train_type      TEXT,                    -- "Rajdhani", "Express", "Mail", "Shatabdi"...
    origin_code     TEXT NOT NULL,           -- "HWH"
    destination_code TEXT NOT NULL,          -- "NDLS"
    pair_train_number TEXT,                  -- "12302" (return journey)
    run_days        TEXT NOT NULL,           -- JSON: ["Mon","Wed","Fri"] or ["Daily"]
    frequency_type  TEXT DEFAULT 'WEEKLY',   -- "DAILY", "WEEKLY", "BIWEEKLY", "SPECIAL"
    total_distance_km INTEGER,
    total_stations  INTEGER,
    is_special      INTEGER DEFAULT 0,       -- 1 for special/one-time trains
    is_active       INTEGER DEFAULT 1,       -- 0 if train discontinued
    alternate_numbers TEXT,                  -- JSON: ["02301"] for diversions
    source          TEXT DEFAULT 'NTES',
    updated_at      TEXT NOT NULL
);

CREATE TABLE train_schedule (
    train_number    TEXT NOT NULL,
    station_code    TEXT NOT NULL,
    sequence        INTEGER NOT NULL,        -- 1, 2, 3... stop order
    scheduled_arrival TEXT,                  -- "09:55" (null for origin)
    scheduled_departure TEXT,                -- "10:00" (null for destination)
    halt_minutes    INTEGER DEFAULT 0,
    distance_km     INTEGER DEFAULT 0,       -- from origin
    day_number      INTEGER DEFAULT 1,       -- day 1, 2, 3 of journey
    halt_type       TEXT DEFAULT 'REGULAR',  -- "REGULAR", "TECHNICAL", "CONDITIONAL"
    platform_default INTEGER,               -- default platform (if known)
    PRIMARY KEY (train_number, station_code, sequence),
    FOREIGN KEY (train_number) REFERENCES trains(train_number),
    FOREIGN KEY (station_code) REFERENCES stations(station_code)
);

-- Daily collected data (grows over time — core of the service)

CREATE TABLE daily_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    train_number    TEXT NOT NULL,
    run_date        TEXT NOT NULL,           -- "2026-04-02"
    run_status      TEXT DEFAULT 'RUNNING',  -- "RUNNING", "COMPLETED", "CANCELLED",
                                             -- "PARTIALLY_CANCELLED", "DIVERTED", "RESCHEDULED"
    actual_origin   TEXT,                    -- may differ from scheduled if partially cancelled
    actual_destination TEXT,                 -- may differ if short-terminated
    is_diverted     INTEGER DEFAULT 0,
    rescheduled_departure TEXT,              -- if origin departure was rescheduled
    data_completeness REAL DEFAULT 0.0,      -- 0.0 to 1.0 — % of stations with actual times
    collection_attempts INTEGER DEFAULT 0,
    last_collected_at TEXT,
    -- Seasonal flags
    is_fog_season       INTEGER DEFAULT 0,
    is_monsoon_season   INTEGER DEFAULT 0,
    is_festival_period  INTEGER DEFAULT 0,
    festival_name       TEXT,                -- "Diwali", "Holi", etc.
    is_public_holiday   INTEGER DEFAULT 0,
    day_of_week         INTEGER NOT NULL,    -- 0=Mon, 6=Sun
    UNIQUE (train_number, run_date)
);

CREATE TABLE daily_stop_times (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    daily_run_id    INTEGER NOT NULL,
    train_number    TEXT NOT NULL,
    run_date        TEXT NOT NULL,
    station_code    TEXT NOT NULL,
    sequence        INTEGER NOT NULL,
    -- Scheduled times
    scheduled_arrival   TEXT,               -- "09:55"
    scheduled_departure TEXT,               -- "10:00"
    -- Actual times
    actual_arrival      TEXT,               -- "10:23" or null if not yet arrived
    actual_departure    TEXT,               -- "10:28" or null
    -- Computed delays (in minutes, can be negative for early arrival)
    delay_arrival_min   INTEGER,            -- 28 (late) or -5 (early)
    delay_departure_min INTEGER,
    -- Metadata
    platform_number     INTEGER,
    halt_type           TEXT DEFAULT 'REGULAR',  -- "REGULAR", "TECHNICAL", "CONDITIONAL"
    stop_status         TEXT DEFAULT 'NORMAL',   -- "NORMAL", "CANCELLED", "SHORT_TERMINATED",
                                                 -- "UNSCHEDULED", "SKIPPED"
    data_status         TEXT DEFAULT 'COLLECTED',-- "COLLECTED", "UNAVAILABLE", "STALE", "ESTIMATED"
    ntes_last_updated   TEXT,               -- timestamp from NTES
    collected_at        TEXT NOT NULL,       -- when we scraped this data
    UNIQUE (train_number, run_date, station_code, sequence),
    FOREIGN KEY (daily_run_id) REFERENCES daily_runs(id),
    FOREIGN KEY (station_code) REFERENCES stations(station_code)
);

-- Predictions (computed by ML engine)

CREATE TABLE predictions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    train_number    TEXT NOT NULL,
    station_code    TEXT NOT NULL,
    prediction_date TEXT NOT NULL,           -- date being predicted for
    predicted_arrival   TEXT,                -- "10:23"
    predicted_departure TEXT,                -- "10:28"
    predicted_delay_min REAL,               -- 28.5
    confidence_pct      REAL NOT NULL,      -- 87.3 (percentage)
    prediction_model    TEXT NOT NULL,       -- "prophet_v1", "sklearn_rf_v1"
    model_features_used TEXT,               -- JSON array of features used
    data_points_used    INTEGER,            -- how many historical runs used
    created_at          TEXT NOT NULL,
    UNIQUE (train_number, station_code, prediction_date, prediction_model)
);

CREATE TABLE reliability_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    train_number    TEXT NOT NULL,
    period_days     INTEGER NOT NULL,       -- 30, 90, 365
    score           REAL NOT NULL,          -- 0-100
    avg_delay_min   REAL,
    median_delay_min REAL,
    on_time_pct     REAL,                   -- % of times delay < 5 min
    late_15_pct     REAL,                   -- % of times delay > 15 min
    late_30_pct     REAL,                   -- % of times delay > 30 min
    late_60_pct     REAL,                   -- % of times delay > 60 min
    cancellation_pct REAL,                  -- % of scheduled runs that were cancelled
    worst_station_code TEXT,                -- station where this train is most delayed
    worst_station_avg_delay REAL,
    total_runs      INTEGER,                -- total data points in period
    computed_at     TEXT NOT NULL,
    UNIQUE (train_number, period_days)
);

-- Metadata & system

CREATE TABLE calendar (
    date            TEXT PRIMARY KEY,        -- "2026-04-02"
    day_of_week     INTEGER NOT NULL,        -- 0=Mon, 6=Sun
    is_public_holiday INTEGER DEFAULT 0,
    holiday_name    TEXT,
    is_fog_season   INTEGER DEFAULT 0,
    is_monsoon_season INTEGER DEFAULT 0,
    is_festival_period INTEGER DEFAULT 0,
    festival_name   TEXT,
    is_exam_season  INTEGER DEFAULT 0,
    season          TEXT                     -- "winter", "summer", "monsoon", "autumn"
);

CREATE TABLE collection_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type        TEXT NOT NULL,           -- "DAILY_RUN_STATUS", "SCHEDULE_REFRESH", "STATION_REFRESH"
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    status          TEXT DEFAULT 'RUNNING',  -- "RUNNING", "COMPLETED", "FAILED", "PARTIAL"
    trains_processed INTEGER DEFAULT 0,
    stations_processed INTEGER DEFAULT 0,
    errors_count    INTEGER DEFAULT 0,
    error_details   TEXT,                    -- JSON array of errors
    duration_seconds REAL
);

-- Indexes for fast queries
CREATE INDEX idx_daily_stop_train_date ON daily_stop_times(train_number, run_date);
CREATE INDEX idx_daily_stop_station_date ON daily_stop_times(station_code, run_date);
CREATE INDEX idx_daily_stop_delay ON daily_stop_times(delay_arrival_min);
CREATE INDEX idx_daily_runs_status ON daily_runs(run_status, run_date);
CREATE INDEX idx_predictions_lookup ON predictions(train_number, station_code, prediction_date);
CREATE INDEX idx_reliability_lookup ON reliability_scores(train_number, period_days);
```

---

## 7. API Design

### Phase 1 MVP Endpoints

#### UC-1: Train ETA Prediction
```
GET /api/v1/trains/{trainNumber}/predict?date=YYYY-MM-DD

Response:
{
    "train_number": "12301",
    "train_name": "Howrah Rajdhani",
    "date": "2026-04-05",
    "prediction_model": "prophet_v1",
    "data_points_used": 142,
    "route": [
        {
            "station_code": "HWH",
            "station_name": "Howrah Junction",
            "sequence": 1,
            "scheduled_departure": "16:55",
            "predicted_departure": "16:55",
            "predicted_delay_min": 0,
            "confidence_pct": 95.2,
            "is_origin": true
        },
        {
            "station_code": "CNB",
            "station_name": "Kanpur Central",
            "sequence": 5,
            "scheduled_arrival": "22:10",
            "predicted_arrival": "22:38",
            "predicted_delay_min": 28,
            "confidence_pct": 87.3,
            "delay_range": {"min": 12, "max": 45},
            "scheduled_departure": "22:15",
            "predicted_departure": "22:43",
            "is_origin": false,
            "is_destination": false
        }
    ],
    "seasonal_note": "Fog season active — delays typically higher on this route",
    "reliability_score": 72
}
```

#### UC-2: Historical Time Graph
```
GET /api/v1/trains/{trainNumber}/stations/{stationCode}/history
    ?period=monthly&from=2026-01-01&to=2026-03-31

Response:
{
    "train_number": "12301",
    "station_code": "CNB",
    "station_name": "Kanpur Central",
    "scheduled_arrival": "22:10",
    "period": "monthly",
    "data_points": [
        {
            "date": "2026-01-05",
            "actual_arrival": "23:45",
            "delay_min": 95,
            "day_of_week": "Monday",
            "flags": ["fog_season"]
        },
        {
            "date": "2026-01-12",
            "actual_arrival": "22:23",
            "delay_min": 13,
            "day_of_week": "Monday",
            "flags": ["fog_season"]
        }
    ],
    "summary": {
        "total_runs": 24,
        "avg_delay_min": 34.2,
        "median_delay_min": 22,
        "on_time_count": 4,
        "cancelled_count": 1
    }
}
```

#### UC-3: Train Reliability Score
```
GET /api/v1/trains/{trainNumber}/reliability?period=90d

Response:
{
    "train_number": "12301",
    "train_name": "Howrah Rajdhani",
    "period": "90d",
    "reliability_score": 72,
    "total_runs": 78,
    "cancelled_runs": 2,
    "avg_delay_min": 23.4,
    "median_delay_min": 15,
    "on_time_pct": 32.1,
    "late_15_min_pct": 55.3,
    "late_30_min_pct": 28.2,
    "late_60_min_pct": 8.1,
    "worst_stations": [
        {"station_code": "CNB", "station_name": "Kanpur Central", "avg_delay_min": 42},
        {"station_code": "MGS", "station_name": "Mughal Sarai", "avg_delay_min": 38}
    ],
    "best_stations": [
        {"station_code": "DHN", "station_name": "Dhanbad", "avg_delay_min": 5}
    ],
    "day_of_week_analysis": {
        "Monday": {"avg_delay": 18, "runs": 12},
        "Friday": {"avg_delay": 35, "runs": 11}
    }
}
```

#### UC-9: Station Live Board
```
GET /api/v1/stations/{stationCode}/board?date=2026-04-02

Response:
{
    "station_code": "CNB",
    "station_name": "Kanpur Central",
    "date": "2026-04-02",
    "arrivals": [
        {
            "train_number": "12301",
            "train_name": "Howrah Rajdhani",
            "origin": "HWH",
            "destination": "NDLS",
            "scheduled_arrival": "22:10",
            "predicted_arrival": "22:38",
            "predicted_delay_min": 28,
            "confidence_pct": 87,
            "reliability_score": 72,
            "platform": 1
        }
    ],
    "departures": [
        {
            "train_number": "12302",
            "train_name": "New Delhi Rajdhani",
            "origin": "NDLS",
            "destination": "HWH",
            "scheduled_departure": "16:30",
            "predicted_departure": "16:35",
            "predicted_delay_min": 5,
            "confidence_pct": 91,
            "reliability_score": 74,
            "platform": 3
        }
    ]
}
```

### Utility Endpoints

```
GET /api/v1/trains                              → List all trains (paginated, searchable)
GET /api/v1/trains/{trainNumber}                → Train details + schedule
GET /api/v1/stations                            → List all stations (paginated, searchable)
GET /api/v1/stations/{stationCode}              → Station details
GET /api/v1/health                              → Service health + last collection status
GET /api/v1/stats                               → Total trains tracked, data points, coverage
```

---

## 8. Data Collection Strategy

### Collection Schedule

| Job | Frequency | Duration | Purpose |
|-----|-----------|----------|---------|
| **Live train status** | Every 30 min (6:00—24:00 IST) | ~45 min per run | Collect actual times for all running trains |
| **End-of-day completion** | 02:00 IST daily | ~30 min | Final sweep for late-running trains, mark day complete |
| **Schedule refresh** | Weekly (Sunday 03:00 IST) | ~2 hours | Update train schedules, detect new/discontinued trains |
| **Station master refresh** | Monthly (1st, 03:00 IST) | ~30 min | Update station data |
| **Prediction recompute** | Daily 04:00 IST | ~1 hour | Recompute predictions for next 7 days |
| **Reliability score refresh** | Daily 04:30 IST | ~30 min | Recompute reliability scores |
| **Calendar update** | Monthly | Seconds | Update holiday/festival flags for next month |
| **Data archival** | Monthly | ~10 min | Move data >12 months to Parquet files |

### Collection Flow (Live Train Status)

```
1. Get list of trains running today (from train_schedule + run_days)
2. For each active train:
   a. Call NTES RunningTrain endpoint
   b. Parse response — extract actual times for each station
   c. Handle edge cases:
      - "Not Yet Started" → skip, will retry next cycle
      - "Cancelled" → mark daily_run as CANCELLED, stop collecting
      - "Diverted" → flag and log alternate route
      - "Data unavailable" → mark as UNAVAILABLE
   d. Upsert into daily_stop_times (idempotent — same data won't create duplicates)
   e. Update daily_runs.data_completeness
3. If all stations have actual times → mark daily_run as COMPLETED
4. Log collection stats to collection_log
5. Sleep until next cycle

Throttling: 1 request per second, max 3600 requests per hour
Rate limit handling: If 429/503 → exponential backoff (5s, 15s, 45s), max 3 retries
User-agent rotation: Pool of 10 user-agent strings, rotate per request
```

---

## 9. Prediction Engine Design

### Model Selection

| Approach | When to Use | Confidence Level |
|----------|-------------|------------------|
| **Facebook Prophet** | Primary model — time-series forecasting with seasonality | High (with >60 data points) |
| **Random Forest** | Secondary model — feature-based prediction | Medium |
| **Simple Average** | Fallback — when <30 data points available | Low |
| **Similar Train Proxy** | When train has <10 data points | Very Low (flagged) |

### Features Used for Prediction

```python
features = {
    # Historical patterns
    "avg_delay_last_30_days": float,
    "avg_delay_same_day_of_week": float,    # e.g., Mondays
    "median_delay_last_90_days": float,
    "delay_std_dev": float,                  # for confidence interval

    # Seasonal
    "is_fog_season": bool,                   # Dec 15 - Feb 15
    "is_monsoon": bool,                      # Jun - Sep
    "is_festival_period": bool,
    "season": str,                           # "winter", "summer"

    # Temporal
    "day_of_week": int,                      # 0-6
    "is_weekend": bool,
    "is_holiday": bool,

    # Route-based
    "preceding_station_avg_delay": float,    # delay tends to propagate
    "distance_from_origin_km": int,          # farther = more delay accumulation
    "station_historical_delay_contribution": float,  # some stations always add delay

    # Train-based
    "train_type": str,                       # Rajdhani > Express in priority
    "is_superfast": bool,
    "total_stops_before_this_station": int,
}
```

### Confidence Score Calculation

```
confidence_pct = base_confidence
    * data_sufficiency_factor       # more data → higher confidence
    * model_accuracy_factor         # cross-validation score
    * seasonal_stability_factor     # fog season → lower confidence
    * recency_factor               # more recent data → higher confidence

Where:
    base_confidence = 90%
    data_sufficiency = min(1.0, data_points / 60)         # 60+ points = full confidence
    model_accuracy = cross_validation_R2_score             # from model training
    seasonal_stability = 0.7 if fog_season else 1.0        # fog adds uncertainty
    recency = 1.0 if latest_data < 7_days else 0.9        # stale data penalty

Result: 0% - 99% (never 100% — always some uncertainty)
```

---

## 10. Phase 1 — MVP Scope & Plan

### What Phase 1 Delivers

- ✅ Automated daily data collection for all trains
- ✅ UC-1: Train ETA prediction at all stations with confidence %
- ✅ UC-2: Historical arrival/departure graph data
- ✅ UC-3: Train reliability score
- ✅ UC-9: Station arrival/departure board with predictions
- ✅ REST API serving predictions and history
- ✅ Self-healing collection with retry logic

### Phase 1 Implementation Steps

| Step | Task | Estimated Effort |
|------|------|-----------------|
| 1 | Project scaffolding (structure, deps, config) | 2 hours |
| 2 | SQLite schema + migration setup | 2 hours |
| 3 | NTES scraper module (with all edge case handling) | 6 hours |
| 4 | Station & train master data loader (one-time seed) | 3 hours |
| 5 | Daily collection scheduler (APScheduler) | 4 hours |
| 6 | Calendar/season flag logic | 1 hour |
| 7 | Prediction engine (Prophet + fallback models) | 6 hours |
| 8 | Reliability score calculator | 2 hours |
| 9 | FastAPI endpoints (UC-1, UC-2, UC-3, UC-9 + utility) | 4 hours |
| 10 | Error handling, retry logic, logging | 3 hours |
| 11 | Testing (unit + integration) | 4 hours |
| 12 | Deployment to free hosting (Render/Fly.io) | 2 hours |
| **Total** | | **~39 hours** |

### Project Structure (Phase 1)

```
train-punctuality-service/
├── pyproject.toml
├── README.md
├── .env.example
├── .github/
│   └── workflows/
│       └── daily-collection.yml       # Backup cron via GitHub Actions
│
├── config/
│   ├── settings.py                    # App configuration
│   ├── constants.py                   # Indian Railways constants
│   └── calendar_data.py               # Holidays, festivals, seasons
│
├── db/
│   ├── schema.sql                     # Full SQLite schema
│   ├── migrations/                    # Schema version tracking
│   └── seed/                          # Initial station/train data
│
├── src/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app entry point
│   │
│   ├── api/                           # REST API layer
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── trains.py              # UC-1, UC-3
│   │   │   ├── stations.py            # UC-9
│   │   │   ├── history.py             # UC-2
│   │   │   └── health.py              # Health check + stats
│   │   └── models/                    # Pydantic response models
│   │       ├── train_models.py
│   │       ├── station_models.py
│   │       └── prediction_models.py
│   │
│   ├── scraper/                       # Data collection layer
│   │   ├── __init__.py
│   │   ├── ntes_client.py             # NTES HTTP client with retry logic
│   │   ├── ntes_parser.py             # Parse NTES responses, handle edge cases
│   │   ├── data_gov_client.py         # data.gov.in API client
│   │   └── erail_scraper.py           # erail.in scraper (backup)
│   │
│   ├── collector/                     # Orchestrates collection
│   │   ├── __init__.py
│   │   ├── scheduler.py               # APScheduler setup
│   │   ├── daily_collector.py         # Main collection loop
│   │   ├── schedule_refresher.py      # Weekly schedule refresh
│   │   └── master_data_loader.py      # One-time station/train seed
│   │
│   ├── prediction/                    # ML prediction engine
│   │   ├── __init__.py
│   │   ├── predictor.py               # Main prediction orchestrator
│   │   ├── prophet_model.py           # Facebook Prophet model
│   │   ├── sklearn_model.py           # Random Forest fallback
│   │   ├── simple_average.py          # Simple average fallback
│   │   ├── confidence.py              # Confidence score calculator
│   │   └── reliability.py             # Reliability score calculator
│   │
│   ├── db/                            # Database layer
│   │   ├── __init__.py
│   │   ├── database.py                # SQLite connection management
│   │   ├── repositories/
│   │   │   ├── train_repo.py
│   │   │   ├── station_repo.py
│   │   │   ├── daily_run_repo.py
│   │   │   ├── prediction_repo.py
│   │   │   └── collection_log_repo.py
│   │   └── models.py                  # DB row dataclasses
│   │
│   └── utils/                         # Shared utilities
│       ├── __init__.py
│       ├── time_utils.py              # IST handling, midnight crossover
│       ├── season_utils.py            # Fog/monsoon/festival detection
│       ├── user_agents.py             # User-agent rotation pool
│       └── logger.py                  # Structured logging
│
├── tests/
│   ├── test_ntes_parser.py
│   ├── test_daily_collector.py
│   ├── test_predictor.py
│   ├── test_reliability.py
│   ├── test_time_utils.py
│   ├── test_api_trains.py
│   └── test_api_stations.py
│
└── scripts/
    ├── seed_data.py                   # Initial data load script
    ├── backfill.py                    # Backfill historical data
    └── export_parquet.py              # Archive old data to Parquet
```

---

## 11. Phase 2 & 3 — Future Roadmap

### Phase 2: Intelligence (after 30+ days of data collection)

| Feature | Depends On |
|---------|------------|
| UC-4: Station delay heatmap | 30+ days of `daily_stop_times` data |
| UC-5: Onward journey planner | Reliable predictions (UC-1) + schedule data |
| UC-7: Route segment analysis | 30+ days data + segment delay computation |
| UC-8: Train comparison | Reliability scores (UC-3) for multiple trains |

### Phase 3: Engagement (after 90+ days of data collection)

| Feature | Depends On |
|---------|------------|
| UC-6: Delay pattern insights | 90+ days data, seasonal coverage |
| UC-10: Alert subscriptions | Email/webhook infrastructure, background jobs |
| Frontend dashboard | All API endpoints stable |

---

## 12. Infrastructure & Hosting

### Free Hosting Options

| Provider | Free Tier | Best For |
|----------|-----------|----------|
| **Render.com** | 750 hrs/mo, auto-sleep after 15 min inactivity | API server |
| **Fly.io** | 3 shared VMs, 3GB storage | Always-on collector |
| **Railway.app** | $5 free credit/month | Quick deployment |
| **PythonAnywhere** | 1 web app, scheduled tasks | Backup scheduler |
| **GitHub Actions** | 2000 min/mo (public repo) | Cron-based collection backup |
| **Supabase** | Free PostgreSQL (500MB) | Alternative to SQLite |

### Recommended Deployment

```
Fly.io VM (always-on):
  ├── FastAPI server (port 8080)
  ├── APScheduler (in-process, runs collection jobs)
  ├── SQLite database (persistent volume)
  └── Prediction engine (runs daily at 04:00 IST)

GitHub Actions (backup):
  └── Cron workflow every 6 hours → triggers /api/v1/internal/collect
      (in case Fly.io scheduler misses a run)
```

---

## 13. Open Questions & Risks

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| NTES blocks scraping | **Critical** — no data collection | User-agent rotation, rate limiting, IP rotation via free proxies |
| NTES changes response format | **High** — parser breaks | Robust error handling, schema versioning, alert on parse failures |
| Free hosting limits exceeded | **Medium** — service goes down | Monitor usage, optimize sleep cycles, fallback to GitHub Actions |
| SQLite performance at scale | **Medium** — slow queries after millions of rows | Index optimization, archive old data to Parquet monthly |
| Prediction accuracy | **Low** — bad predictions reduce trust | Always show confidence %, transparent about data limitations |

### Open Questions

1. Should we also track platform changes? (useful for passenger experience)
2. Should we expose a public frontend or API-only service initially?
3. Do we need user accounts, or is it fully anonymous/public?
4. Should we persist predictions for audit trail, or compute on-the-fly?
5. What's the maximum acceptable latency for prediction API? (<500ms target)

---

*Last updated: 2026-04-02*
*Next milestone: Phase 1 MVP — project scaffolding and NTES scraper proof-of-concept*
