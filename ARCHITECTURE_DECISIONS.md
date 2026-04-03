# Architecture Decisions

## Hosting (all $0)

| Component | Service | Free Tier Limits |
|-----------|---------|-----------------|
| **Data collector** | GitHub Actions (cron) | Unlimited mins (public repo), 7GB RAM |
| **Database** | Turso (cloud SQLite) | 5GB storage, 500M reads/mo, 10M writes/mo |
| **API server** | Render.com (web service) | 750 hrs/mo, sleeps after 15min idle |

## Key Decisions

1. **Playwright required for NTES** — httpx gets blocked by WAF. Playwright headless Chromium works and extracts real delay data.
2. **Collector runs on GitHub Actions** — 7GB RAM handles Chromium easily. Cron schedule, not always-on.
3. **Turso as shared DB** — both GitHub Actions and Render connect over HTTPS. No file sync needed. libsql is SQLite-compatible.
4. **Render for API only** — lightweight FastAPI, no Playwright at runtime. Reads from Turso. Cold start ~1 min after idle is acceptable.
5. **erail.in for train metadata** — `getTrains.aspx` returns structured data via simple HTTP. Used for schedule/run days/train type.
6. **No AWS/Amazon resources** — confirmed, everything is on free non-Amazon infrastructure.

## Data Sources Validated

| Source | Method | Data | Status |
|--------|--------|------|--------|
| NTES (enquiry.indianrail.gov.in) | Playwright | Live running status, actual times, delays | ✅ Working |
| erail.in/rail/getTrains.aspx | httpx GET | Train info, schedule, run days, type | ✅ Working |
| data.gov.in | REST API | Station master data | ✅ Working |

## What Didn't Work

- NTES via httpx — WAF blocks, returns empty responses even with CSRF token
- indianrailapi.com — "Server busy" errors
- railwayapi.com — domain dead
- confirmtkt API — 404s on all endpoints
- erail.in route/live endpoints — return HTML pages, not data
