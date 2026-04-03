from datetime import date
from src.utils.season_utils import (
    is_fog_season, is_monsoon_season, get_holiday, get_festival_period, get_season,
)


class TestFogSeason:
    def test_dec_15_start(self):
        assert is_fog_season(date(2026, 12, 15)) is True

    def test_dec_14_not_fog(self):
        assert is_fog_season(date(2026, 12, 14)) is False

    def test_jan_mid(self):
        assert is_fog_season(date(2026, 1, 15)) is True

    def test_feb_15_end(self):
        assert is_fog_season(date(2026, 2, 15)) is True

    def test_feb_16_not_fog(self):
        assert is_fog_season(date(2026, 2, 16)) is False

    def test_summer_not_fog(self):
        assert is_fog_season(date(2026, 5, 1)) is False

    def test_dec_31(self):
        assert is_fog_season(date(2026, 12, 31)) is True

    def test_jan_1(self):
        assert is_fog_season(date(2026, 1, 1)) is True


class TestMonsoonSeason:
    def test_jun_1_start(self):
        assert is_monsoon_season(date(2026, 6, 1)) is True

    def test_sep_30_end(self):
        assert is_monsoon_season(date(2026, 9, 30)) is True

    def test_may_31_not_monsoon(self):
        assert is_monsoon_season(date(2026, 5, 31)) is False

    def test_oct_1_not_monsoon(self):
        assert is_monsoon_season(date(2026, 10, 1)) is False

    def test_jul_mid(self):
        assert is_monsoon_season(date(2026, 7, 15)) is True


class TestHoliday:
    def test_republic_day(self):
        assert get_holiday(date(2026, 1, 26)) == "Republic Day"

    def test_independence_day(self):
        assert get_holiday(date(2026, 8, 15)) == "Independence Day"

    def test_not_a_holiday(self):
        assert get_holiday(date(2026, 4, 3)) is None

    def test_christmas(self):
        assert get_holiday(date(2026, 12, 25)) == "Christmas"


class TestFestivalPeriod:
    def test_diwali_start(self):
        assert get_festival_period(date(2026, 10, 28)) == "Diwali"

    def test_diwali_end(self):
        assert get_festival_period(date(2026, 11, 3)) == "Diwali"

    def test_holi(self):
        assert get_festival_period(date(2026, 3, 17)) == "Holi"

    def test_not_festival(self):
        assert get_festival_period(date(2026, 4, 3)) is None

    def test_chhath_puja(self):
        assert get_festival_period(date(2026, 11, 6)) == "Chhath Puja"


class TestSeason:
    def test_winter(self):
        assert get_season(date(2026, 1, 15)) == "winter"
        assert get_season(date(2026, 12, 1)) == "winter"

    def test_summer(self):
        assert get_season(date(2026, 4, 15)) == "summer"

    def test_monsoon(self):
        assert get_season(date(2026, 7, 15)) == "monsoon"

    def test_autumn(self):
        assert get_season(date(2026, 10, 15)) == "autumn"
