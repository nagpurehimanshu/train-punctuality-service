from src.utils.time_utils import compute_delay_minutes, parse_hhmm
from datetime import timedelta


class TestParseHHMM:
    def test_normal(self):
        assert parse_hhmm("09:55") == timedelta(hours=9, minutes=55)

    def test_midnight(self):
        assert parse_hhmm("00:00") == timedelta(0)

    def test_end_of_day(self):
        assert parse_hhmm("23:59") == timedelta(hours=23, minutes=59)

    def test_none(self):
        assert parse_hhmm(None) is None

    def test_empty(self):
        assert parse_hhmm("") is None

    def test_whitespace(self):
        assert parse_hhmm("  09:55  ") == timedelta(hours=9, minutes=55)


class TestComputeDelayMinutes:
    def test_on_time(self):
        assert compute_delay_minutes("09:55", "09:55") == 0

    def test_late(self):
        assert compute_delay_minutes("09:55", "10:23") == 28

    def test_early(self):
        assert compute_delay_minutes("09:55", "09:50") == -5

    def test_one_minute_late(self):
        assert compute_delay_minutes("22:35", "22:36") == 1

    def test_large_delay(self):
        assert compute_delay_minutes("10:00", "14:30") == 270  # 4.5 hours

    def test_midnight_crossover_late(self):
        # Scheduled 23:50, arrived 00:10 next day
        result = compute_delay_minutes("23:50", "00:10")
        assert result == 20

    def test_midnight_crossover_on_time(self):
        # Scheduled 23:55, arrived 00:00
        result = compute_delay_minutes("23:55", "00:00")
        assert result == 5

    def test_midnight_crossover_with_day_offset(self):
        # day_offset=1 means actual is explicitly on the next calendar day
        # Scheduled 23:50 day 1, actual 00:10 day 2 = 20 min late
        # The auto-detection already handles this, day_offset just confirms it
        result = compute_delay_minutes("23:50", "00:10", day_offset=1)
        assert result == 20

    def test_none_scheduled(self):
        assert compute_delay_minutes(None, "10:00") is None

    def test_none_actual(self):
        assert compute_delay_minutes("10:00", None) is None

    def test_both_none(self):
        assert compute_delay_minutes(None, None) is None

    def test_origin_station_no_arrival(self):
        # Origin has no arrival, only departure
        assert compute_delay_minutes(None, "16:50") is None

    def test_destination_no_departure(self):
        assert compute_delay_minutes("10:05", None) is None
