# On-time threshold in minutes — delay <= this is considered "on time"
ON_TIME_THRESHOLD_MIN = 5

# Outlier threshold — delays beyond this excluded from prediction models
OUTLIER_DELAY_THRESHOLD_MIN = 360  # 6 hours

# Minimum data points for each prediction model tier
MIN_POINTS_PROPHET = 60
MIN_POINTS_SKLEARN = 30
MIN_POINTS_AVERAGE = 10

# Confidence caps based on data sufficiency
MAX_CONFIDENCE_LOW_DATA = 40.0  # <10 runs

# Fog season: Dec 15 — Feb 15
FOG_SEASON_START = (12, 15)
FOG_SEASON_END = (2, 15)

# Monsoon season: Jun 1 — Sep 30
MONSOON_START = (6, 1)
MONSOON_END = (9, 30)

# NTES scraping
NTES_MAX_RETRIES = 3
NTES_RETRY_BACKOFF = [5, 15, 45]  # seconds
NTES_REQUEST_TIMEOUT = 30  # seconds
