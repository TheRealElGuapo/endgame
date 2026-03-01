-- MySQL schema for deathpool database

-- Participants table
CREATE TABLE IF NOT EXISTS participants (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Celebrity picks table
CREATE TABLE IF NOT EXISTS picks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    participant_id INT NOT NULL,
    celebrity_name VARCHAR(255) NOT NULL,
    birth_date DATE DEFAULT NULL,
    age INT DEFAULT NULL,
    death_date DATE DEFAULT NULL,
    death_age INT DEFAULT NULL,
    points INT DEFAULT 0,
    is_first_blood TINYINT DEFAULT 0,
    season_year INT NOT NULL,
    wikipedia_url TEXT DEFAULT NULL,
    description TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (participant_id) REFERENCES participants(id) ON DELETE CASCADE
);

CREATE INDEX idx_season ON picks(season_year);
CREATE INDEX idx_participant_season ON picks(participant_id, season_year);

-- Season configuration table
CREATE TABLE IF NOT EXISTS season_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    season_year INT NOT NULL UNIQUE,
    end_date DATETIME NOT NULL,
    first_blood_winner_id INT DEFAULT NULL,
    picks_locked TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (first_blood_winner_id) REFERENCES participants(id) ON DELETE SET NULL
);
