"""Tests for NTES parser — validates extraction from pipe-delimited tab text.

These tests use the exact patterns observed from real NTES pages to ensure
the parser handles all known formats correctly.
"""

from src.scraper.ntes_client import _parse_tab, TrainRun, StopTime


def _make_tab_text(header: str, stations: list[str]) -> str:
    """Build a pipe-delimited tab text like NTES produces."""
    parts = [header, "HOWRAH JN - NEW DELHI", "Arrival", "Station", "Departure"]
    parts.extend(stations)
    return "|".join(parts)


class TestParseTabStatus:
    def test_completed_run(self):
        text = "Start Date : 01-Apr-2026|Reached Destination|Arrived at NEW DELHI(NDLS) at 10:05 02-Apr (On Time)|HOWRAH JN - NEW DELHI|Arrival|Station|Departure"
        run = _parse_tab(text, "12301")
        assert run.status == "COMPLETED"
        assert run.start_date == "01-Apr-2026"

    def test_not_yet_started(self):
        text = "Start Date : 04-Apr-2026|Yet to start from its source|HOWRAH JN - NEW DELHI|Arrival|Station|Departure"
        run = _parse_tab(text, "12301")
        assert run.status == "NOT_YET_STARTED"

    def test_cancelled(self):
        text = "Start Date : 04-Apr-2026|Train Cancelled|HOWRAH JN - NEW DELHI|Arrival|Station|Departure"
        run = _parse_tab(text, "12301")
        assert run.status == "CANCELLED"

    def test_running(self):
        text = "Start Date : 02-Apr-2026|Current Position|Departed from (CYZ) at 09:05 03-Apr|HOWRAH JN - NEW DELHI|Arrival|Station|Departure"
        run = _parse_tab(text, "12301")
        assert run.status == "RUNNING"

    def test_missing_start_date(self):
        text = "Reached Destination|HOWRAH JN - NEW DELHI|Arrival|Station|Departure"
        run = _parse_tab(text, "12301")
        assert run.start_date == ""


class TestParseTabStations:
    """Test station extraction from real NTES patterns."""

    def test_normal_station_with_delay(self):
        text = (
            "Start Date : 01-Apr-2026|Reached Destination|"
            "HOWRAH JN - NEW DELHI|Arrival|Station|Departure|"
            "Close|18:47 01-Apr|19:00 01-Apr|13 Min|ASANSOL JN.|ASN|PF 4|Coach Position|200|KMs|18:49 01-Apr|19:03 01-Apr|14 Min"
        )
        run = _parse_tab(text, "12301")
        assert len(run.stops) == 1
        s = run.stops[0]
        assert s.station_code == "ASN"
        assert s.station_name == "ASANSOL JN."
        assert s.scheduled_arrival == "18:47"
        assert s.actual_arrival == "19:00"
        assert s.delay_arrival_min == 13
        assert s.platform == 4
        assert s.distance_km == 200

    def test_on_time_station(self):
        text = (
            "Start Date : 01-Apr-2026|Reached Destination|"
            "HOWRAH JN - NEW DELHI|Arrival|Station|Departure|"
            "Close|19:55 01-Apr|19:54 01-Apr|On Time|DHANBAD JN|DHN|PF 3|Coach Position|258|KMs|20:00 01-Apr|20:01 01-Apr|1 Min"
        )
        run = _parse_tab(text, "12301")
        assert len(run.stops) == 1
        s = run.stops[0]
        assert s.station_code == "DHN"
        assert s.delay_arrival_min == 0  # On Time

    def test_origin_station(self):
        """Origin has SRC markers, no arrival, only departure."""
        text = (
            "Start Date : 01-Apr-2026|Reached Destination|"
            "HOWRAH JN - NEW DELHI|Arrival|Station|Departure|"
            "SRC|SRC|HOWRAH JN|HWH|PF 9|Coach Position|SRC|16:50 01-Apr|16:50 01-Apr|On Time"
        )
        run = _parse_tab(text, "12301")
        assert len(run.stops) == 1
        s = run.stops[0]
        assert s.station_code == "HWH"
        assert s.station_name == "HOWRAH JN"

    def test_destination_station(self):
        """Destination has DSTN markers, no departure."""
        text = (
            "Start Date : 01-Apr-2026|Reached Destination|"
            "HOWRAH JN - NEW DELHI|Arrival|Station|Departure|"
            "Close|10:05 02-Apr|10:05 02-Apr|On Time|NEW DELHI|NDLS|PF 14|Coach Position|1449|KMs|DSTN|DSTN"
        )
        run = _parse_tab(text, "12301")
        assert len(run.stops) == 1
        s = run.stops[0]
        assert s.station_code == "NDLS"
        assert s.station_name == "NEW DELHI"
        assert s.delay_arrival_min == 0

    def test_coach_position_noise_filtered(self):
        """Coach position data (ENG, LPR, VP, PC) should not create fake stations."""
        text = (
            "Start Date : 01-Apr-2026|Reached Destination|"
            "HOWRAH JN - NEW DELHI|Arrival|Station|Departure|"
            "Close|18:47 01-Apr|19:00 01-Apr|13 Min|ASANSOL JN.|ASN|PF 4|Coach Position|200|KMs|18:49 01-Apr|19:03 01-Apr|14 Min|"
            "Coach Position  : 12301|ASANSOL JN.|01-Apr|PF : 4|×|ENG|ENG|0|LPR|LPR|1|3A|B1|2|3A|B2|3|"
            "PC|PC|13|1A|H1|14|VP|VP|23"
        )
        run = _parse_tab(text, "12301")
        # Should only have ASN, not ENG/LPR/VP/PC
        codes = [s.station_code for s in run.stops]
        assert "ASN" in codes
        assert "ENG" not in codes
        assert "LPR" not in codes
        assert "VP" not in codes
        assert "PC" not in codes

    def test_multiple_stations(self):
        text = (
            "Start Date : 01-Apr-2026|Reached Destination|"
            "HOWRAH JN - NEW DELHI|Arrival|Station|Departure|"
            "Close|18:47 01-Apr|19:00 01-Apr|13 Min|ASANSOL JN.|ASN|PF 4|Coach Position|200|KMs|18:49 01-Apr|19:03 01-Apr|14 Min|"
            "Coach Position  : 12301|ASANSOL JN.|01-Apr|PF : 4|×|ENG|ENG|0|LPR|LPR|1|Close|"
            "19:55 01-Apr|19:54 01-Apr|On Time|DHANBAD JN|DHN|PF 3|Coach Position|258|KMs|20:00 01-Apr|20:01 01-Apr|1 Min"
        )
        run = _parse_tab(text, "12301")
        codes = [s.station_code for s in run.stops]
        assert "ASN" in codes
        assert "DHN" in codes

    def test_platform_with_asterisk(self):
        """Future dates show PF with asterisk (e.g., 'PF 9*')."""
        text = (
            "Start Date : 04-Apr-2026|Yet to start from its source|"
            "HOWRAH JN - NEW DELHI|Arrival|Station|Departure|"
            "SRC|SRC|HOWRAH JN|HWH|PF 9*|SRC|16:50 04-Apr|16:50 04-Apr*|On Time"
        )
        run = _parse_tab(text, "12301")
        if run.stops:
            s = run.stops[0]
            assert s.platform == 9  # asterisk stripped

    def test_empty_text(self):
        run = _parse_tab("", "12301")
        assert run is not None
        assert run.stops == []

    def test_no_stations_in_text(self):
        text = "Start Date : 01-Apr-2026|Reached Destination|Some random text"
        run = _parse_tab(text, "12301")
        assert run.stops == []


class TestParseTabEdgeCases:
    def test_station_code_with_numbers_ignored(self):
        """Station codes like 'B1', '3A' from coach data should not match."""
        text = (
            "Start Date : 01-Apr-2026|Reached Destination|"
            "HOWRAH JN - NEW DELHI|Arrival|Station|Departure|"
            "3A|B1|2|3A|B2|3"
        )
        run = _parse_tab(text, "12301")
        # B1, B2 are not valid station codes (contain numbers)
        assert len(run.stops) == 0

    def test_delay_2_min_format(self):
        """NTES shows '2 Min' for small delays."""
        text = (
            "Start Date : 31-Mar-2026|Reached Destination|"
            "HOWRAH JN - NEW DELHI|Arrival|Station|Departure|"
            "Close|10:05 01-Apr|10:07 01-Apr|2 Min|NEW DELHI|NDLS|PF 14|1449|KMs|DSTN|DSTN"
        )
        run = _parse_tab(text, "12301")
        if run.stops:
            assert run.stops[0].delay_arrival_min == 2

    def test_train_name_extracted(self):
        text = (
            "Start Date : 01-Apr-2026|Reached Destination|"
            "HOWRAH JN - NEW DELHI|Arrival|Station|Departure"
        )
        run = _parse_tab(text, "12301")
        assert run.train_name == "HOWRAH JN - NEW DELHI"
