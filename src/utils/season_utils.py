"""Seasonal and calendar flag detection."""

from datetime import date
from config.constants import FOG_SEASON_START, FOG_SEASON_END, MONSOON_START, MONSOON_END
from config.calendar_data import PUBLIC_HOLIDAYS_2026, FESTIVAL_PERIODS_2026


def is_fog_season(d: date) -> bool:
    m, day = d.month, d.day
    # Dec 15 — Feb 15
    if m == 12 and day >= FOG_SEASON_START[1]:
        return True
    if m == 1:
        return True
    if m == 2 and day <= FOG_SEASON_END[1]:
        return True
    return False


def is_monsoon_season(d: date) -> bool:
    return (MONSOON_START[0], MONSOON_START[1]) <= (d.month, d.day) <= (MONSOON_END[0], MONSOON_END[1])


def get_holiday(d: date) -> str | None:
    for hdate, name in PUBLIC_HOLIDAYS_2026:
        if d == hdate:
            return name
    return None


def get_festival_period(d: date) -> str | None:
    for start, end, name in FESTIVAL_PERIODS_2026:
        if start <= d <= end:
            return name
    return None


def get_season(d: date) -> str:
    m = d.month
    if m in (12, 1, 2):
        return "winter"
    if m in (3, 4, 5):
        return "summer"
    if m in (6, 7, 8, 9):
        return "monsoon"
    return "autumn"
