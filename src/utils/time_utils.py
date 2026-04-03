"""IST time handling and delay computation."""

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    return datetime.now(IST)


def today_ist() -> str:
    return now_ist().strftime("%Y-%m-%d")


def parse_hhmm(time_str: str | None) -> timedelta | None:
    """Parse 'HH:MM' to timedelta from midnight."""
    if not time_str:
        return None
    h, m = map(int, time_str.strip().split(":"))
    return timedelta(hours=h, minutes=m)


def compute_delay_minutes(
    scheduled: str | None, actual: str | None, day_offset: int = 0
) -> int | None:
    """Compute delay in minutes between scheduled and actual HH:MM times.

    day_offset handles midnight crossover — if actual is on the next day relative
    to scheduled, pass day_offset=1.
    """
    s = parse_hhmm(scheduled)
    a = parse_hhmm(actual)
    if s is None or a is None:
        return None
    a = a + timedelta(days=day_offset)
    diff = a - s
    # Handle midnight crossover: if actual appears much earlier than scheduled
    # and no explicit day_offset, it likely crossed midnight
    if day_offset == 0 and diff.total_seconds() < -12 * 3600:
        diff += timedelta(days=1)
    return int(diff.total_seconds() / 60)
