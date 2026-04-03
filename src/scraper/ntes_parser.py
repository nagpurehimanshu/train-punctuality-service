"""Parse NTES HTML responses into structured data."""

from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from src.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class StopTime:
    station_code: str
    station_name: str
    sequence: int
    scheduled_arrival: str | None = None
    scheduled_departure: str | None = None
    actual_arrival: str | None = None
    actual_departure: str | None = None
    delay_arrival_min: int | None = None
    delay_departure_min: int | None = None
    platform: int | None = None
    halt_type: str = "REGULAR"
    stop_status: str = "NORMAL"
    data_status: str = "COLLECTED"


@dataclass
class RunningStatus:
    train_number: str
    train_name: str = ""
    run_date: str = ""
    status: str = "RUNNING"  # RUNNING, COMPLETED, CANCELLED, NOT_YET_STARTED
    stops: list[StopTime] = field(default_factory=list)


@dataclass
class ScheduleStop:
    station_code: str
    station_name: str
    sequence: int
    arrival: str | None = None
    departure: str | None = None
    halt_minutes: int = 0
    distance_km: int = 0
    day_number: int = 1


def parse_running_status(html: str, train_number: str) -> RunningStatus | None:
    """Parse NTES running status HTML into RunningStatus.

    NTES response format varies — this parser handles the common table-based layout.
    Returns None if the response can't be parsed or train is not found.
    """
    if not html or "no running" in html.lower() or "not found" in html.lower():
        return None

    soup = BeautifulSoup(html, "html.parser")
    result = RunningStatus(train_number=train_number)

    # Check for cancellation
    text = soup.get_text(separator=" ").lower()
    if "cancelled" in text:
        result.status = "CANCELLED"
        return result
    if "not yet started" in text or "not started" in text:
        result.status = "NOT_YET_STARTED"
        return result

    # Extract train name from header if present
    header = soup.find(["h3", "h4", "div"], class_=lambda c: c and "train" in str(c).lower())
    if header:
        result.train_name = header.get_text(strip=True)

    # Parse station rows from table
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for seq, row in enumerate(rows):
            cells = row.find_all(["td", "th"])
            if len(cells) < 4:
                continue
            cell_texts = [c.get_text(strip=True) for c in cells]
            stop = _parse_stop_row(cell_texts, seq)
            if stop:
                result.stops.append(stop)

    if result.stops:
        # Check if journey is complete (all stops have actual times)
        all_have_actual = all(
            (s.actual_arrival or s.sequence == 1) and (s.actual_departure or s.sequence == len(result.stops))
            for s in result.stops
        )
        if all_have_actual:
            result.status = "COMPLETED"

    return result


def _parse_stop_row(cells: list[str], sequence: int) -> StopTime | None:
    """Try to extract a StopTime from a table row's cell texts.

    NTES table columns vary but typically include:
    station_code/name, scheduled_arr, scheduled_dep, actual_arr, actual_dep, delay, platform
    """
    # Skip header rows
    if any(h in cells[0].lower() for h in ["station", "stn", "s.no", "#"]):
        return None

    try:
        # Heuristic: first cell is station info, rest are times
        station_text = cells[0]
        stn_code = ""
        stn_name = station_text

        # Try to split "NDLS/New Delhi" or "NDLS - New Delhi" patterns
        for sep in ["/", " - ", "-"]:
            if sep in station_text:
                parts = station_text.split(sep, 1)
                stn_code = parts[0].strip().upper()
                stn_name = parts[1].strip()
                break

        if not stn_code:
            stn_code = station_text.strip().upper()[:5]

        stop = StopTime(station_code=stn_code, station_name=stn_name, sequence=sequence)

        # Extract times from remaining cells — positions vary
        time_cells = cells[1:]
        times = [_clean_time(t) for t in time_cells]

        if len(times) >= 2:
            stop.scheduled_arrival = times[0]
            stop.scheduled_departure = times[1]
        if len(times) >= 4:
            stop.actual_arrival = times[2]
            stop.actual_departure = times[3]
        if len(times) >= 5:
            stop.delay_arrival_min = _parse_delay(times[4])

        # Platform — look for a numeric cell near the end
        for t in reversed(time_cells):
            t_clean = t.strip()
            if t_clean.isdigit() and int(t_clean) < 20:
                stop.platform = int(t_clean)
                break

        return stop
    except Exception as e:
        log.debug(f"Could not parse stop row {cells}: {e}")
        return None


def _clean_time(raw: str) -> str | None:
    """Clean a time string, return HH:MM or None."""
    raw = raw.strip().replace(".", ":").replace(" ", "")
    if not raw or raw == "--" or raw.lower() in ("na", "n/a", "source", "right time"):
        return None
    if raw.upper() == "RT":
        return "RT"  # Right Time — means on schedule
    # Extract HH:MM pattern
    parts = raw.split(":")
    if len(parts) == 2 and parts[0].isdigit() and parts[1][:2].isdigit():
        return f"{int(parts[0]):02d}:{int(parts[1][:2]):02d}"
    return None


def _parse_delay(raw: str) -> int | None:
    """Parse delay string like '28 min late', 'Right Time', '-5'."""
    raw = raw.strip().lower()
    if not raw or raw in ("--", "na"):
        return None
    if "right time" in raw or raw == "rt":
        return 0
    # Extract numeric part
    num = ""
    for ch in raw:
        if ch.isdigit() or ch == "-":
            num += ch
    if num:
        try:
            return int(num)
        except ValueError:
            return None
    return None


def parse_train_schedule(html: str, train_number: str) -> list[ScheduleStop]:
    """Parse NTES train schedule HTML into list of ScheduleStop."""
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    stops: list[ScheduleStop] = []

    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for seq, row in enumerate(rows):
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            cell_texts = [c.get_text(strip=True) for c in cells]
            if any(h in cell_texts[0].lower() for h in ["station", "stn", "s.no"]):
                continue
            try:
                stn_text = cell_texts[0]
                stn_code = stn_text.split("/")[0].strip().upper() if "/" in stn_text else stn_text.strip().upper()[:5]
                stn_name = stn_text.split("/")[1].strip() if "/" in stn_text else stn_text

                stop = ScheduleStop(
                    station_code=stn_code,
                    station_name=stn_name,
                    sequence=seq,
                    arrival=_clean_time(cell_texts[1]) if len(cell_texts) > 1 else None,
                    departure=_clean_time(cell_texts[2]) if len(cell_texts) > 2 else None,
                )
                if len(cell_texts) > 3 and cell_texts[3].isdigit():
                    stop.halt_minutes = int(cell_texts[3])
                if len(cell_texts) > 4 and cell_texts[4].isdigit():
                    stop.distance_km = int(cell_texts[4])
                if len(cell_texts) > 5 and cell_texts[5].isdigit():
                    stop.day_number = int(cell_texts[5])

                stops.append(stop)
            except Exception as e:
                log.debug(f"Could not parse schedule row {cell_texts}: {e}")

    return stops
