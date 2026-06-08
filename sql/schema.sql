-- AFL Tipping Factory Schema

CREATE TABLE IF NOT EXISTS matches (
    match_id         TEXT PRIMARY KEY,
    season           INTEGER NOT NULL,
    round            INTEGER NOT NULL,
    match_date       TEXT,
    kickoff_time     TEXT,
    venue            TEXT,
    neutral_venue    INTEGER DEFAULT 0,
    home_team        TEXT NOT NULL,
    away_team        TEXT NOT NULL,
    bookie_favourite TEXT,
    home_odds        REAL,
    away_odds        REAL,
    implied_home_prob REAL,
    implied_away_prob REAL,
    elo_expected_margin REAL,
    elo_margin_sd    REAL,
    elo_home_prob    REAL,
    elo_away_prob    REAL,
    actual_winner    TEXT,
    home_score       INTEGER,
    away_score       INTEGER,
    actual_margin    INTEGER,
    market_source    TEXT,
    market_last_update TEXT
);

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id          TEXT NOT NULL,
    model_name        TEXT NOT NULL,
    predicted_winner  TEXT NOT NULL,
    predicted_home_prob REAL,
    predicted_away_prob REAL,
    confidence_score  REAL,
    confidence_rating TEXT,
    faded_favourite   INTEGER DEFAULT 0,
    fade_successful   INTEGER,
    was_correct       INTEGER,
    rationale         TEXT,
    created_at        TEXT DEFAULT (datetime('now')),
    UNIQUE(match_id, model_name),
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

CREATE TABLE IF NOT EXISTS odds_snapshots (
    snapshot_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id      TEXT NOT NULL,
    home_odds     REAL NOT NULL,
    away_odds     REAL NOT NULL,
    market_source TEXT NOT NULL,
    snapshot_time TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

CREATE TABLE IF NOT EXISTS match_features (
    match_id              TEXT PRIMARY KEY,
    home_rest_days        REAL,
    away_rest_days        REAL,
    home_travel_km_14d    REAL,
    away_travel_km_14d    REAL,
    neutral_venue         INTEGER DEFAULT 0,
    interstate_travel     INTEGER DEFAULT 0,
    home_ground_advantage REAL,
    indoor_venue          INTEGER DEFAULT 0,
    rain_forecast_mm      REAL DEFAULT 0,
    wind_kmh              REAL DEFAULT 0,
    key_forward_out       INTEGER DEFAULT 0,
    key_defender_out      INTEGER DEFAULT 0,
    ruck_disrupted        INTEGER DEFAULT 0,
    midfield_disrupted    INTEGER DEFAULT 0,
    captain_out           INTEGER DEFAULT 0,
    short_turnaround      INTEGER DEFAULT 0,
    ladder_position_home  REAL,
    ladder_position_away  REAL,
    percentage_home       REAL,
    percentage_away       REAL,
    recent_form_home      REAL,
    recent_form_away      REAL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

CREATE TABLE IF NOT EXISTS elo_ratings (
    team        TEXT PRIMARY KEY,
    rating      REAL NOT NULL DEFAULT 1500.0,
    season      INTEGER,
    updated_at  TEXT DEFAULT (datetime('now'))
);
