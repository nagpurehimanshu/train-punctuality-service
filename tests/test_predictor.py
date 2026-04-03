from src.prediction.predictor import _compute_confidence, _add_minutes


class TestComputeConfidence:
    def test_very_low_data(self):
        # 2 data points → capped at MAX_CONFIDENCE_LOW_DATA
        c = _compute_confidence(2, 5, 10, 7.5)
        assert c == 8.0  # 2 * 4.0

    def test_low_data_threshold(self):
        # Exactly 10 points (MIN_POINTS_AVERAGE) → enters normal formula
        c = _compute_confidence(10, 0, 20, 10)
        assert 5 <= c <= 50

    def test_high_data_low_variance(self):
        # 100 points, tight range → high confidence
        c = _compute_confidence(100, 3, 8, 5)
        assert c >= 80

    def test_high_data_high_variance(self):
        # 100 points but huge spread → lower confidence
        c = _compute_confidence(100, 0, 180, 40)
        assert c < 70

    def test_never_exceeds_99(self):
        c = _compute_confidence(1000, 5, 6, 5.5)
        assert c <= 99.0

    def test_never_below_5_with_enough_data(self):
        c = _compute_confidence(15, 0, 500, 100)
        assert c >= 5.0

    def test_zero_data_points(self):
        c = _compute_confidence(0, 0, 0, 0)
        assert c == 0.0


class TestAddMinutes:
    def test_normal(self):
        assert _add_minutes("10:00", 28) == "10:28"

    def test_zero_delay(self):
        assert _add_minutes("10:00", 0) == "10:00"

    def test_negative_delay(self):
        assert _add_minutes("10:00", -5) == "09:55"

    def test_crosses_midnight(self):
        assert _add_minutes("23:50", 20) == "00:10"

    def test_none_input(self):
        assert _add_minutes(None, 10) is None

    def test_fractional_rounds(self):
        assert _add_minutes("10:00", 5.7) == "10:06"

    def test_large_delay(self):
        assert _add_minutes("10:00", 180) == "13:00"  # 3 hours

    def test_wraps_full_day(self):
        # 25 hours of delay wraps around
        assert _add_minutes("10:00", 25 * 60) == "11:00"
