# Deathpool 2025

A Flask web app to track your deathpool competition with friends.

## Features

- **Leaderboard**: Real-time scoring with "100 minus age" formula
- **First Blood**: Track the first death of the season as a separate side bet
- **Age Lookup**: Automatically fetch celebrity ages from Wikipedia
- **Manual Death Recording**: Mark deaths with specific dates
- **Season Countdown**: Track time remaining until Feb 17, 2025 at 23:59:59

## Setup

1. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

2. Database is already set up with your picks (150 total picks from Jim, Drew, and Oost)

## Running the App

Start the Flask server:
```bash
python3 app.py
```

Then open your browser to: **http://127.0.0.1:5000**

## Usage

### Lookup Ages
- Click "🔍 Lookup Age" on any pick to automatically fetch the celebrity's age from Wikipedia
- This will calculate their current age and save their birth date

### Mark a Death
1. Click "☠️ Mark Death" on a pick
2. Enter the date of death
3. Points are automatically calculated (100 - age at death)
4. The first death of the season automatically wins the "First Blood" side bet

### Undo a Death
- If you marked someone by mistake, click "↶ Undo" to remove the death marking

## Scoring

- **Main Pool**: 100 minus age at death (younger = more points)
- **First Blood**: Separate side bet for the first death of the season
- Season ends: February 17, 2025 at 23:59:59

## Database

The app uses MySQL:
- Database: `deathpool`
- Tables: `participants`, `picks`, `season_config`

## Tech Stack

- Flask (Python web framework)
- MySQL (database)
- Wikipedia API (age lookup)
- Vanilla JavaScript (frontend interactivity)
