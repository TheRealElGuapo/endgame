-- SQLite schema for deathpool database

-- Participants table
CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    username TEXT UNIQUE,
    password_hash TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Celebrity picks table
CREATE TABLE IF NOT EXISTS picks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER NOT NULL,
    celebrity_name TEXT NOT NULL,
    birth_date DATE DEFAULT NULL,
    age INTEGER DEFAULT NULL,
    death_date DATE DEFAULT NULL,
    death_age INTEGER DEFAULT NULL,
    points INTEGER DEFAULT 0,
    is_first_blood INTEGER DEFAULT 0,
    season_year INTEGER NOT NULL,
    wikipedia_url TEXT DEFAULT NULL,
    description TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (participant_id) REFERENCES participants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_season ON picks(season_year);
CREATE INDEX IF NOT EXISTS idx_participant_season ON picks(participant_id, season_year);

-- Season configuration table
CREATE TABLE IF NOT EXISTS season_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_year INTEGER NOT NULL UNIQUE,
    end_date DATETIME NOT NULL,
    first_blood_winner_id INTEGER DEFAULT NULL,
    picks_locked INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (first_blood_winner_id) REFERENCES participants(id) ON DELETE SET NULL
);

-- Insert current season
INSERT OR REPLACE INTO season_config (season_year, end_date)
VALUES (2025, '2025-02-17 23:59:59');
