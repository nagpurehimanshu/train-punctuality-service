from __future__ import annotations

"""NTES scraper using Playwright headless browser.

NTES is JS-rendered with CSRF protection — httpx gets blocked.
Playwright loads the page like a real browser and extracts data from the rendered DOM.
"""


import re
from dataclasses import dataclass, field
from playwright.sync_api import sync_playwright, Browser, Page
from src.utils.logger import get_logger

log = get_logger(__name__)

NTES_URL = "https://enquiry.indianrail.gov.in/mntes/"

# Known station codes to filter out coach position noise (ENG, LPR, VP, PC etc.)
_COACH_CODES = {"ENG", "LPR", "VP", "PC", "SRC", "DSTN"}
_DELAY_RE = re.compile(r"(\d+)\s*Min", re.IGNORECASE)
_TIME_RE = re.compile(r"(\d{2}:\d{2})\s+(\d{2}-\w{3})")


@dataclass
class StopTime:
    station_code: str
    station_name: str
    sequence: int
    scheduled_arrival: str | None = None
    actual_arrival: str | None = None
    delay_arrival_min: int | None = None
    scheduled_departure: str | None = None
    actual_departure: str | None = None
    delay_departure_min: int | None = None
    platform: int | None = None
    distance_km: int | None = None


@dataclass
class TrainRun:
    train_number: str
    train_name: str = ""
    start_date: str = ""  # DD-Mon-YYYY
    status: str = "RUNNING"  # RUNNING, COMPLETED, CANCELLED, NOT_YET_STARTED
    stops: list[StopTime] = field(default_factory=list)


def scrape_train(train_number: str, browser: Browser) -> list[TrainRun]:
    """Scrape NTES for a train's running status. Returns runs for all dates shown."""
    page = browser.new_page()
    try:
        page.goto(NTES_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        page.fill('input[name="trainNo"]', train_number)
        page.wait_for_timeout(1000)
        page.keyboard.press("Enter")
        page.wait_for_timeout(8000)

        return _parse_page(page, train_number)
    except Exception as e:
        log.error(f"Failed to scrape {train_number}: {e}")
        return []
    finally:
        page.close()


def scrape_single_date(train_number: str, browser: Browser) -> TrainRun | None:
    """Scrape and return only the most recent completed run."""
    runs = scrape_train(train_number, browser)
    for run in runs:
        if run.status == "COMPLETED":
            return run
    return runs[0] if runs else None


def _parse_page(page: Page, train_number: str) -> list[TrainRun]:
    """Parse all tab-panes from the NTES page into TrainRun objects."""
    from bs4 import BeautifulSoup

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    tabs = soup.find_all(class_="tab-pane")

    runs: list[TrainRun] = []
    for tab in tabs:
        text = tab.get_text(separator="|", strip=True)
        if not text or "Arrival" not in text:
            continue
        run = _parse_tab(text, train_number)
        if run and run.stops:
            runs.append(run)
    return runs


def _parse_tab(text: str, train_number: str) -> TrainRun | None:
    """Parse a single tab-pane's pipe-delimited text into a TrainRun."""
    parts = [p.strip() for p in text.split("|") if p.strip()]
    run = TrainRun(train_number=train_number)

    # Extract start date: "Start Date : DD-Mon-YYYY"
    for p in parts:
        if "Start Date" in p:
            m = re.search(r"(\d{2}-\w{3}-\d{4})", p)
            if m:
                run.start_date = m.group(1)
            break

    # Determine status
    joined = " ".join(parts[:20]).lower()
    if "reached destination" in joined:
        run.status = "COMPLETED"
    elif "yet to start" in joined:
        run.status = "NOT_YET_STARTED"
        return run
    elif "cancelled" in joined:
        run.status = "CANCELLED"
        return run

    # Extract train name from "HOWRAH JN - NEW DELHI" pattern
    for p in parts:
        if " - " in p and any(c.isupper() for c in p):
            run.train_name = p
            break

    # Parse stations — look for the repeating pattern:
    # sched_arr date | actual_arr date | delay | STATION_NAME | STN_CODE | PF N | ... | distance | KMs | sched_dep date | actual_dep date | delay
    seq = 0
    i = 0
    in_coach_block = False
    while i < len(parts):
        p = parts[i]

        # Track coach position blocks — skip everything inside them
        if "Coach Position" in p and ":" in p:
            in_coach_block = True
            i += 1
            continue
        if in_coach_block:
            if p == "Close" or (i + 1 < len(parts) and _TIME_RE.search(parts[i + 1]) and p not in ("×", "Note - Data shown with (*) are dynamic in nature and may change.")):
                in_coach_block = False
                if p == "Close":
                    i += 1
                    continue
            else:
                i += 1
                continue

        # Station detection: look for a known station code pattern
        # Station codes are 2-5 uppercase alpha, NOT in coach codes, preceded by station name
        if (
            2 <= len(p) <= 5
            and p.isalpha()
            and p.isupper()
            and p not in _COACH_CODES
            and i >= 1
            and not parts[i - 1].startswith("PF")
            and "Coach" not in parts[i - 1]
        ):
            stn_code = p
            stn_name = parts[i - 1] if i > 0 else ""

            # Skip if station name looks like noise
            if stn_name in ("Close", "×", "Arrival", "Station", "Departure", ""):
                i += 1
                continue

            seq += 1
            stop = StopTime(station_code=stn_code, station_name=stn_name, sequence=seq)

            # Look backwards for arrival times (before station name)
            _extract_arrival(parts, i - 1, stop)

            # Look forward for platform, distance, departure times
            _extract_forward(parts, i + 1, stop)

            run.stops.append(stop)

        i += 1

    return run


def _extract_arrival(parts: list[str], name_idx: int, stop: StopTime):
    """Extract scheduled/actual arrival and delay from parts before station name."""
    # Pattern before station name: ... | sched_arr | actual_arr | delay | STATION_NAME
    # Look back up to 4 positions
    window = parts[max(0, name_idx - 4) : name_idx]
    times = []
    delay = None
    for w in window:
        if w in ("Close", "×", "Coach Position", "Note") or "Coach Position" in w:
            continue
        tm = _TIME_RE.search(w)
        if tm:
            times.append(tm.group(1))
        dm = _DELAY_RE.search(w)
        if dm:
            delay = int(dm.group(1))
        if w == "On Time":
            delay = 0

    if len(times) >= 2:
        stop.scheduled_arrival = times[-2]
        stop.actual_arrival = times[-1]
    elif len(times) == 1:
        stop.scheduled_arrival = times[0]

    stop.delay_arrival_min = delay


def _extract_forward(parts: list[str], start_idx: int, stop: StopTime):
    """Extract platform, distance, departure times from parts after station code."""
    window = parts[start_idx : start_idx + 12]
    times = []
    delay = None

    for w in window:
        # Platform
        if w.startswith("PF"):
            pf = w.replace("PF", "").strip().rstrip("*")
            if pf.isdigit():
                stop.platform = int(pf)

        # Distance
        if w == "KMs" and times == []:
            # Previous part was the distance
            idx = window.index(w)
            if idx > 0:
                d = window[idx - 1].rstrip("*")
                if d.isdigit():
                    stop.distance_km = int(d)

        # Departure times
        tm = _TIME_RE.search(w)
        if tm:
            times.append(tm.group(1))

        dm = _DELAY_RE.search(w)
        if dm:
            delay = int(dm.group(1))
        if w == "On Time":
            delay = 0

        # Stop at next station's data (Coach Position signals end)
        if "Coach Position" in w and ":" in w:
            break

    if len(times) >= 2:
        stop.scheduled_departure = times[0]
        stop.actual_departure = times[1]
    elif len(times) == 1:
        stop.scheduled_departure = times[0]

    if stop.delay_departure_min is None:
        stop.delay_departure_min = delay


def create_browser() -> Browser:
    """Create a reusable Playwright browser instance."""
    pw = sync_playwright().start()
    return pw.chromium.launch(headless=True)
