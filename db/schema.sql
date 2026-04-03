-- Reference data

CREATE TABLE IF NOT EXISTS stations (
    station_code    TEXT PRIMARY KEY,
    station_name    TEXT NOT NULL,
    zone            TEXT,
    division        TEXT,
    state           TEXT,
    latitude        REAL,
    longitude       REAL,
    station_category TEXT,
    num_platforms   INTEGER,
    aliases         TEXT,  -- JSON array
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trains (
    train_number    TEXT PRIMARY KEY,
    train_name      TEXT NOT NULL,
    train_type      TEXT,
    origin_code     TEXT NOT NULL,
    destination_code TEXT NOT NULL,
    pair_train_number TEXT,
    run_days        TEXT NOT NULL,  -- JSON array
    frequency_type  TEXT DEFAULT 'WEEKLY',
    total_distance_km INTEGER,
    total_stations  INTEGER,
    is_special      INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1,
    alternate_numbers TEXT,  -- JSON array
    source          TEXT DEFAULT 'NTES',
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS train_schedule (
    train_number    TEXT NOT NULL,
    station_code    TEXT NOT NULL,
    sequence        INTEGER NOT NULL,
    scheduled_arrival TEXT,
    scheduled_departure TEXT,
    halt_minutes    INTEGER DEFAULT 0,
    distance_km     INTEGER DEFAULT 0,
    day_number      INTEGER DEFAULT 1,
    halt_type       TEXT DEFAULT 'REGULAR',
    platform_default INTEGER,
    PRIMARY KEY (train_number, station_code, sequence),
    FOREIGN KEY (train_number) REFERENCES trains(train_number),
    FOREIGN KEY (station_code) REFERENCES stations(station_code)
);

-- Daily collected data

CREATE TABLE IF NOT EXISTS daily_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    train_number    TEXT NOT NULL,
    run_date        TEXT NOT NULL,
    run_status      TEXT DEFAULT 'RUNNING',
    actual_origin   TEXT,
    actual_destination TEXT,
    is_diverted     INTEGER DEFAULT 0,
    rescheduled_departure TEXT,
    data_completeness REAL DEFAULT 0.0,
    collection_attempts INTEGER DEFAULT 0,
    last_collected_at TEXT,
    is_fog_season       INTEGER DEFAULT 0,
    is_monsoon_season   INTEGER DEFAULT 0,
    is_festival_period  INTEGER DEFAULT 0,
    festival_name       TEXT,
    is_public_holiday   INTEGER DEFAULT 0,
    day_of_week         INTEGER NOT NULL,
    UNIQUE (train_number, run_date)
);

CREATE TABLE IF NOT EXISTS daily_stop_times (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    daily_run_id    INTEGER NOT NULL,
    train_number    TEXT NOT NULL,
    run_date        TEXT NOT NULL,
    station_code    TEXT NOT NULL,
    sequence        INTEGER NOT NULL,
    scheduled_arrival   TEXT,
    scheduled_departure TEXT,
    actual_arrival      TEXT,
    actual_departure    TEXT,
    delay_arrival_min   INTEGER,
    delay_departure_min INTEGER,
    platform_number     INTEGER,
    halt_type           TEXT DEFAULT 'REGULAR',
    stop_status         TEXT DEFAULT 'NORMAL',
    data_status         TEXT DEFAULT 'COLLECTED',
    ntes_last_updated   TEXT,
    collected_at        TEXT NOT NULL,
    UNIQUE (train_number, run_date, station_code, sequence),
    FOREIGN KEY (daily_run_id) REFERENCES daily_runs(id),
    FOREIGN KEY (station_code) REFERENCES stations(station_code)
);

-- Predictions

CREATE TABLE IF NOT EXISTS predictions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    train_number    TEXT NOT NULL,
    station_code    TEXT NOT NULL,
    prediction_date TEXT NOT NULL,
    predicted_arrival   TEXT,
    predicted_departure TEXT,
    predicted_delay_min REAL,
    confidence_pct      REAL NOT NULL,
    prediction_model    TEXT NOT NULL,
    model_features_used TEXT,
    data_points_used    INTEGER,
    created_at          TEXT NOT NULL,
    UNIQUE (train_number, station_code, prediction_date, prediction_model)
);

CREATE TABLE IF NOT EXISTS reliability_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    train_number    TEXT NOT NULL,
    period_days     INTEGER NOT NULL,
    score           REAL NOT NULL,
    avg_delay_min   REAL,
    median_delay_min REAL,
    on_time_pct     REAL,
    late_15_pct     REAL,
    late_30_pct     REAL,
    late_60_pct     REAL,
    cancellation_pct REAL,
    worst_station_code TEXT,
    worst_station_avg_delay REAL,
    total_runs      INTEGER,
    computed_at     TEXT NOT NULL,
    UNIQUE (train_number, period_days)
);

-- Metadata

CREATE TABLE IF NOT EXISTS calendar (
    date            TEXT PRIMARY KEY,
    day_of_week     INTEGER NOT NULL,
    is_public_holiday INTEGER DEFAULT 0,
    holiday_name    TEXT,
    is_fog_season   INTEGER DEFAULT 0,
    is_monsoon_season INTEGER DEFAULT 0,
    is_festival_period INTEGER DEFAULT 0,
    festival_name   TEXT,
    is_exam_season  INTEGER DEFAULT 0,
    season          TEXT
);

CREATE TABLE IF NOT EXISTS collection_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type        TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    status          TEXT DEFAULT 'RUNNING',
    trains_processed INTEGER DEFAULT 0,
    stations_processed INTEGER DEFAULT 0,
    errors_count    INTEGER DEFAULT 0,
    error_details   TEXT,
    duration_seconds REAL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_daily_stop_train_date ON daily_stop_times(train_number, run_date);
CREATE INDEX IF NOT EXISTS idx_daily_stop_station_date ON daily_stop_times(station_code, run_date);
CREATE INDEX IF NOT EXISTS idx_daily_stop_delay ON daily_stop_times(delay_arrival_min);
CREATE INDEX IF NOT EXISTS idx_daily_runs_status ON daily_runs(run_status, run_date);
CREATE INDEX IF NOT EXISTS idx_predictions_lookup ON predictions(train_number, station_code, prediction_date);
CREATE INDEX IF NOT EXISTS idx_reliability_lookup ON reliability_scores(train_number, period_days);
