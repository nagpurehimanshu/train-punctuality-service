# Architecture Decisions

## Hosting (all $0)

| Component | Service | Free Tier Limits |
|-----------|---------|-----------------|
| **Data collector** | GitHub Actions (cron) + Oracle VM SOCKS proxy | GH Actions: 2000 min/mo free; Oracle VM: Always Free |
| **Database** | Turso (cloud SQLite, Mumbai) | 5GB storage, 500M reads/mo, 10M writes/mo |
| **API server** | Render.com (web service) | 750 hrs/mo, sleeps after 15min idle |

## Key Decisions

1. **Playwright required for NTES** — httpx gets blocked by WAF. Playwright headless Chromium works and extracts real delay data.
2. **GitHub Actions + Oracle VM SOCKS proxy** — NTES blocks non-Indian IPs. GitHub Actions runs the collector (Playwright + Python) and opens an SSH SOCKS5 tunnel (`ssh -D 1080`) to an Oracle Cloud VM in India. Playwright routes all traffic through the tunnel, exiting via the VM's Indian IP. The VM acts as a dumb proxy — no Python, no Playwright, no cron installed on it.
3. **Manual lib install via rpm2cpio** — The VM has only 503MB RAM. yum/dnf load repo metadata into memory and cause OOM + SSH lockout. Solution: download RPMs with curl, extract .so files with rpm2cpio+cpio, copy to /usr/lib64. Zero memory overhead.
4. **2.5GB swap file** — Added to handle Playwright/Chromium memory spikes during scraping.
5. **Turso as shared DB** — both Oracle VM and Render connect over HTTPS. No file sync needed. libsql is SQLite-compatible.
6. **Render for API only** — lightweight FastAPI, no Playwright at runtime. Reads from Turso. Cold start ~1 min after idle is acceptable.
7. **erail.in for train metadata** — `getTrains.aspx` returns structured data via simple HTTP. Used for schedule/run days/train type.
8. **No AWS/Amazon resources** — everything is on free non-Amazon infrastructure.

## Data Sources Validated

| Source | Method | Data | Status |
|--------|--------|------|--------|
| NTES (enquiry.indianrail.gov.in) | Playwright | Live running status, actual times, delays | ✅ Working |
| erail.in/rail/getTrains.aspx | httpx GET | Train info, schedule, run days, type | ✅ Working |
| data.gov.in | REST API | Station master data | ✅ Working |

## What Didn't Work

- **NTES via httpx** — WAF blocks, returns empty responses even with CSRF token
- **GitHub Actions for collection (direct)** — NTES blocks US/EU IPs; solved by routing through Oracle VM SOCKS proxy
- **yum/dnf on 503MB VM** — loads full repo metadata into RAM, causes OOM, kills sshd, requires reboot
- **Oracle ARM instance (24GB)** — Always Free but perpetually out of capacity in India regions
- indianrailapi.com — "Server busy" errors
- railwayapi.com — domain dead
- confirmtkt API — 404s on all endpoints
- erail.in route/live endpoints — return HTML pages, not data

## Oracle VM Setup Notes

The VM required manual Chromium dependency installation because package managers OOM on 503MB RAM:

```bash
# Pattern for each missing lib (10 total):
curl -sLO https://yum.oracle.com/repo/OracleLinux/OL9/appstream/x86_64/getPackage/<package>.rpm
sudo rpm2cpio <package>.rpm | sudo cpio -idm
sudo cp -a usr/lib64/lib<name>* /usr/lib64/
```

Libraries installed: atk, at-spi2-atk, at-spi2-core, libXcomposite, libXdamage, libXfixes, libXrandr, mesa-libgbm, libxkbcommon, alsa-lib, libXi, libdrm
