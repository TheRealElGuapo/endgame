-- Create deathpool database
CREATE DATABASE IF NOT EXISTS deathpool CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE deathpool;

-- Participants table
CREATE TABLE IF NOT EXISTS participants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Celebrity picks table
CREATE TABLE IF NOT EXISTS picks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    participant_id INT NOT NULL,
    celebrity_name VARCHAR(255) NOT NULL,
    birth_date DATE DEFAULT NULL,
    age INT DEFAULT NULL,
    death_date DATE DEFAULT NULL,
    death_age INT DEFAULT NULL,
    points INT DEFAULT 0,
    is_first_blood BOOLEAN DEFAULT FALSE,
    season_year INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (participant_id) REFERENCES participants(id) ON DELETE CASCADE,
    INDEX idx_season (season_year),
    INDEX idx_participant_season (participant_id, season_year)
);

-- Season configuration table
CREATE TABLE IF NOT EXISTS season_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    season_year INT NOT NULL UNIQUE,
    end_date DATETIME NOT NULL,
    first_blood_winner_id INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (first_blood_winner_id) REFERENCES participants(id) ON DELETE SET NULL
);

-- Insert current season
INSERT INTO season_config (season_year, end_date)
VALUES (2025, '2025-02-17 23:59:59')
ON DUPLICATE KEY UPDATE end_date = '2025-02-17 23:59:59';
