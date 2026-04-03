"""Indian public holidays and major festivals for seasonal flagging."""

from datetime import date

# Major public holidays (fixed dates, update yearly)
PUBLIC_HOLIDAYS_2026 = [
    (date(2026, 1, 26), "Republic Day"),
    (date(2026, 3, 10), "Maha Shivaratri"),
    (date(2026, 3, 17), "Holi"),
    (date(2026, 4, 6), "Ram Navami"),
    (date(2026, 4, 14), "Ambedkar Jayanti"),
    (date(2026, 5, 1), "May Day"),
    (date(2026, 5, 24), "Buddha Purnima"),
    (date(2026, 6, 27), "Eid ul-Fitr"),
    (date(2026, 8, 15), "Independence Day"),
    (date(2026, 8, 22), "Janmashtami"),
    (date(2026, 9, 3), "Eid ul-Adha"),
    (date(2026, 10, 2), "Gandhi Jayanti"),
    (date(2026, 10, 12), "Dussehra"),
    (date(2026, 10, 31), "Diwali"),
    (date(2026, 11, 1), "Diwali (Day 2)"),
    (date(2026, 11, 19), "Guru Nanak Jayanti"),
    (date(2026, 12, 25), "Christmas"),
]

# Festival periods (date ranges with heavy travel)
FESTIVAL_PERIODS_2026 = [
    (date(2026, 3, 15), date(2026, 3, 19), "Holi"),
    (date(2026, 10, 9), date(2026, 10, 14), "Dussehra"),
    (date(2026, 10, 28), date(2026, 11, 3), "Diwali"),
    (date(2026, 11, 4), date(2026, 11, 8), "Chhath Puja"),
    (date(2026, 12, 23), date(2026, 12, 31), "Christmas/New Year"),
]
