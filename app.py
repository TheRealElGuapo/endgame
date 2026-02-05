from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime
import requests
import re
from contextlib import contextmanager
import os

app = Flask(__name__)

# Database configuration
DB_PATH = os.environ.get('DB_PATH', 'deathpool.db')

def dict_factory(cursor, row):
    """Convert database rows to dictionaries"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    try:
        yield conn
    finally:
        conn.close()

def get_wikipedia_age(celebrity_name):
    """Fetch age from Wikipedia using their API"""
    try:
        # Search for the person on Wikipedia
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            'action': 'query',
            'list': 'search',
            'srsearch': celebrity_name,
            'format': 'json',
            'srlimit': 1
        }

        headers = {
            'User-Agent': 'DeathpoolApp/1.0 (Educational project; Python/Requests)'
        }

        print(f"Looking up: {celebrity_name}")
        response = requests.get(search_url, params=search_params, headers=headers, timeout=10)
        print(f"Search response status: {response.status_code}")

        if response.status_code != 200:
            print(f"Error: Got status {response.status_code}")
            return None, None

        data = response.json()
        print(f"Search results: {len(data.get('query', {}).get('search', []))} found")

        if not data.get('query', {}).get('search'):
            return None, None

        # Get the page content and description
        page_title = data['query']['search'][0]['title']
        print(f"Found page: {page_title}")

        content_params = {
            'action': 'query',
            'prop': 'revisions|description',
            'titles': page_title,
            'rvprop': 'content',
            'format': 'json',
            'rvslots': 'main'
        }

        response = requests.get(search_url, params=content_params, headers=headers, timeout=10)
        print(f"Content response status: {response.status_code}")

        if response.status_code != 200:
            print(f"Error: Got status {response.status_code}")
            return None, None

        pages = response.json()['query']['pages']
        page = list(pages.values())[0]

        if 'revisions' not in page:
            return None

        content = page['revisions'][0]['slots']['main']['*']
        description = page.get('description', '')

        # Try to find birth date in the infobox
        birth_date_patterns = [
            r'birth_date\s*=\s*\{\{(?:birth date and age|birth date)\|(?:df=yes\|)?(\d{4})\|(\d{1,2})\|(\d{1,2})',
            r'birth_date\s*=\s*\{\{dob\|(?:df=yes\|)?(\d{4})\|(\d{1,2})\|(\d{1,2})',
            r'birth_date\s*=\s*\{\{bda\|(?:df=yes\|)?(\d{4})\|(\d{1,2})\|(\d{1,2})',
            r'birth_date\s*=\s*\{\{(?:birth date and age|birth date)\|(?:mf=yes\|)?(\d{4})\|(\d{1,2})\|(\d{1,2})',
        ]

        birth_date = None
        birth_dt = None

        for pattern in birth_date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                year, month, day = match.groups()
                birth_date = f"{year}-{int(month):02d}-{int(day):02d}"
                birth_dt = datetime.strptime(birth_date, '%Y-%m-%d')
                break

        if not birth_date:
            print(f"Could not find birth date in Wikipedia content for {celebrity_name}")
            return None

        # Try to find death date in the infobox (handles nested templates like {{circa|{{death date...}}}})
        death_date_patterns = [
            r'death_date\s*=\s*\{\{(?:circa\|)?\{\{(?:death date and age|death date)\|(?:df=yes\|)?(\d{4})\|(\d{1,2})\|(\d{1,2})',
            r'death_date\s*=\s*\{\{(?:death date and age|death date)\|(?:df=yes\|)?(\d{4})\|(\d{1,2})\|(\d{1,2})',
            r'death_date\s*=\s*\{\{dda\|(?:df=yes\|)?(\d{4})\|(\d{1,2})\|(\d{1,2})',
            r'death_date\s*=\s*\{\{(?:death date and age|death date)\|(?:mf=yes\|)?(\d{4})\|(\d{1,2})\|(\d{1,2})',
        ]

        death_date = None
        death_age = None

        for pattern in death_date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                year, month, day = match.groups()
                death_date = f"{year}-{int(month):02d}-{int(day):02d}"
                death_dt = datetime.strptime(death_date, '%Y-%m-%d')
                death_age = death_dt.year - birth_dt.year - ((death_dt.month, death_dt.day) < (birth_dt.month, birth_dt.day))
                break

        # Calculate current age (or age at death)
        if death_date:
            age = death_age
        else:
            today = datetime.now()
            age = today.year - birth_dt.year - ((today.month, today.day) < (birth_dt.month, birth_dt.day))

        wiki_url = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"

        result = {
            'age': age,
            'birth_date': birth_date,
            'death_date': death_date,
            'death_age': death_age,
            'wiki_url': wiki_url,
            'description': description
        }

        if death_date:
            print(f"✓ Found {celebrity_name}: Age {age}, DECEASED on {death_date}")
        else:
            print(f"✓ Found {celebrity_name}: Age {age} years old")

        return result
    except Exception as e:
        print(f"Error fetching age for {celebrity_name}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

@app.route('/')
def index():
    """Main dashboard showing leaderboard and all picks"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get current season
        cursor.execute("SELECT * FROM season_config WHERE season_year = 2025")
        season = cursor.fetchone()

        # Calculate time remaining
        end_date = season['end_date']
        time_remaining = end_date - datetime.now()
        days_remaining = max(0, time_remaining.days)
        hours_remaining = max(0, time_remaining.seconds // 3600) if days_remaining >= 0 else 0

        # Get leaderboard
        cursor.execute("""
            SELECT
                p.name,
                p.id,
                COALESCE(SUM(pk.points), 0) as total_points,
                COUNT(CASE WHEN pk.death_date IS NOT NULL THEN 1 END) as deaths_count
            FROM participants p
            LEFT JOIN picks pk ON p.id = pk.participant_id AND pk.season_year = 2025
            GROUP BY p.id, p.name
            ORDER BY total_points DESC, deaths_count DESC
        """)
        leaderboard = cursor.fetchall()

        # Get first blood info (all picks with the earliest death date - handles ties)
        cursor.execute("""
            SELECT p.name, pk.celebrity_name, pk.death_date, pk.death_age, pk.points
            FROM picks pk
            JOIN participants p ON pk.participant_id = p.id
            WHERE pk.death_date = (
                SELECT MIN(death_date)
                FROM picks
                WHERE death_date IS NOT NULL AND season_year = 2025
            )
            AND pk.season_year = 2025
            ORDER BY p.name
        """)
        first_blood_picks = cursor.fetchall()

        # Get all picks with details
        cursor.execute("""
            SELECT
                pk.*,
                p.name as participant_name
            FROM picks pk
            JOIN participants p ON pk.participant_id = p.id
            WHERE pk.season_year = 2025
            ORDER BY p.name, pk.celebrity_name
        """)
        all_picks = cursor.fetchall()

        # Determine first blood picks (all with earliest death date) and mark them
        first_blood_pick_ids = set()
        if first_blood_picks:
            # Get the earliest death date
            earliest_death_date = first_blood_picks[0]['death_date']
            # Find all pick IDs with this death date
            first_blood_pick_ids = {
                pick['id'] for pick in all_picks
                if pick['death_date'] == earliest_death_date
            }

        # Group picks by participant and mark first blood
        picks_by_participant = {}
        for pick in all_picks:
            # Dynamically set is_first_blood based on earliest death
            pick['is_first_blood'] = (pick['id'] in first_blood_pick_ids)

            participant = pick['participant_name']
            if participant not in picks_by_participant:
                picks_by_participant[participant] = []
            picks_by_participant[participant].append(pick)

        # Define season start for validation (use date, not datetime)
        from datetime import date
        season_start = date(2025, 1, 1)

        return render_template('index.html',
                             leaderboard=leaderboard,
                             first_blood_picks=first_blood_picks,
                             picks_by_participant=picks_by_participant,
                             days_remaining=days_remaining,
                             hours_remaining=hours_remaining,
                             season_end=end_date.strftime('%B %d, %Y at %I:%M:%S %p'),
                             season_start=season_start)

@app.route('/lookup_age/<int:pick_id>')
def lookup_age(pick_id):
    """Look up age for a specific pick"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT celebrity_name, participant_id FROM picks WHERE id = %s", (pick_id,))
        pick = cursor.fetchone()

        if not pick:
            return jsonify({'error': 'Pick not found'}), 404

        result = get_wikipedia_age(pick['celebrity_name'])

        if result and result['age'] is not None:
            if result['death_date']:
                # Celebrity is deceased - calculate points and check for first blood
                points = max(0, 100 - result['death_age'])

                cursor.execute("""
                    SELECT COUNT(*) as death_count
                    FROM picks
                    WHERE season_year = 2025 AND death_date IS NOT NULL
                """)
                is_first_blood = (cursor.fetchone()['death_count'] == 0)

                cursor.execute("""
                    UPDATE picks
                    SET age = %s, birth_date = %s, death_date = %s, death_age = %s,
                        points = %s, is_first_blood = %s, wikipedia_url = %s, description = %s
                    WHERE id = %s
                """, (result['age'], result['birth_date'], result['death_date'],
                      result['death_age'], points, is_first_blood, result['wiki_url'], result['description'], pick_id))

                if is_first_blood:
                    cursor.execute("""
                        UPDATE season_config
                        SET first_blood_winner_id = %s
                        WHERE season_year = 2025
                    """, (pick['participant_id'],))
            else:
                # Celebrity is alive
                cursor.execute("""
                    UPDATE picks
                    SET age = %s, birth_date = %s, wikipedia_url = %s, description = %s
                    WHERE id = %s
                """, (result['age'], result['birth_date'], result['wiki_url'], result['description'], pick_id))

            conn.commit()

            return jsonify({
                'success': True,
                'age': result['age'],
                'birth_date': result['birth_date'],
                'death_date': result['death_date'],
                'deceased': result['death_date'] is not None
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not find age information'
            })

@app.route('/mark_death/<int:pick_id>', methods=['POST'])
def mark_death(pick_id):
    """Mark a celebrity as deceased and calculate points"""
    death_date = request.form.get('death_date')

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get pick details
        cursor.execute("SELECT * FROM picks WHERE id = %s", (pick_id,))
        pick = cursor.fetchone()

        if not pick:
            return jsonify({'error': 'Pick not found'}), 404

        # If no age is set, try to look it up first
        if pick['age'] is None:
            age, birth_date = get_wikipedia_age(pick['celebrity_name'])
            if age is not None:
                cursor.execute("""
                    UPDATE picks
                    SET age = %s, birth_date = %s
                    WHERE id = %s
                """, (age, birth_date, pick_id))
                conn.commit()
                pick['age'] = age
                pick['birth_date'] = birth_date

        # Calculate death age and points
        death_dt = datetime.strptime(death_date, '%Y-%m-%d')

        if pick['birth_date']:
            birth_dt = datetime.strptime(str(pick['birth_date']), '%Y-%m-%d')
            death_age = death_dt.year - birth_dt.year - ((death_dt.month, death_dt.day) < (birth_dt.month, birth_dt.day))
        else:
            # If we don't have exact birth date, use current age as estimate
            death_age = pick['age'] if pick['age'] else 0

        points = max(0, 100 - death_age)

        # Check if this is the first death of the season (First Blood)
        cursor.execute("""
            SELECT COUNT(*) as death_count
            FROM picks
            WHERE season_year = 2025 AND death_date IS NOT NULL
        """)
        result = cursor.fetchone()
        is_first_blood = (result['death_count'] == 0)

        # Update the pick
        cursor.execute("""
            UPDATE picks
            SET death_date = %s, death_age = %s, points = %s, is_first_blood = %s
            WHERE id = %s
        """, (death_date, death_age, points, is_first_blood, pick_id))

        # If first blood, update season config
        if is_first_blood:
            cursor.execute("""
                UPDATE season_config
                SET first_blood_winner_id = %s
                WHERE season_year = 2025
            """, (pick['participant_id'],))

        conn.commit()

        return redirect(url_for('index'))

@app.route('/unmark_death/<int:pick_id>', methods=['POST'])
def unmark_death(pick_id):
    """Remove death marking from a pick"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check if this was first blood
        cursor.execute("SELECT is_first_blood FROM picks WHERE id = %s", (pick_id,))
        pick = cursor.fetchone()

        # Clear death information
        cursor.execute("""
            UPDATE picks
            SET death_date = NULL, death_age = NULL, points = 0, is_first_blood = FALSE
            WHERE id = %s
        """, (pick_id,))

        # If it was first blood, clear the season config
        if pick and pick['is_first_blood']:
            cursor.execute("""
                UPDATE season_config
                SET first_blood_winner_id = NULL
                WHERE season_year = 2025
            """)

        conn.commit()

        return redirect(url_for('index'))

@app.route('/add_pick', methods=['POST'])
def add_pick():
    """Add a new pick for a participant"""
    participant_id = request.form.get('participant_id')
    celebrity_name = request.form.get('celebrity_name')

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO picks (participant_id, celebrity_name, season_year)
            VALUES (%s, %s, 2025)
        """, (participant_id, celebrity_name))

        conn.commit()

        return redirect(url_for('index'))

@app.route('/delete_pick/<int:pick_id>', methods=['POST'])
def delete_pick(pick_id):
    """Delete a pick"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM picks WHERE id = %s", (pick_id,))
        conn.commit()

        return redirect(url_for('index'))

@app.route('/update_date/<int:pick_id>', methods=['POST'])
def update_date(pick_id):
    """Update birth or death date for a pick"""
    data = request.get_json()
    date_type = data.get('date_type')  # 'birth' or 'death'
    new_date = data.get('new_date')

    if date_type not in ['birth', 'death']:
        return jsonify({'success': False, 'error': 'Invalid date type'}), 400

    if not new_date:
        return jsonify({'success': False, 'error': 'No date provided'}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor()

        if date_type == 'birth':
            # Update birth date and recalculate age
            cursor.execute("SELECT * FROM picks WHERE id = %s", (pick_id,))
            pick = cursor.fetchone()

            birth_dt = datetime.strptime(new_date, '%Y-%m-%d')

            if pick['death_date']:
                # Recalculate death age
                death_dt = pick['death_date']
                death_age = death_dt.year - birth_dt.year - ((death_dt.month, death_dt.day) < (birth_dt.month, birth_dt.day))
                age = death_age
                points = max(0, 100 - death_age)

                cursor.execute("""
                    UPDATE picks
                    SET birth_date = %s, age = %s, death_age = %s, points = %s
                    WHERE id = %s
                """, (new_date, age, death_age, points, pick_id))
            else:
                # Just update birth date and current age
                today = datetime.now()
                age = today.year - birth_dt.year - ((today.month, today.day) < (birth_dt.month, birth_dt.day))

                cursor.execute("""
                    UPDATE picks
                    SET birth_date = %s, age = %s
                    WHERE id = %s
                """, (new_date, age, pick_id))

        elif date_type == 'death':
            # Update death date and recalculate death age and points
            cursor.execute("SELECT * FROM picks WHERE id = %s", (pick_id,))
            pick = cursor.fetchone()

            if not pick['birth_date']:
                return jsonify({'success': False, 'error': 'Cannot set death date without birth date'}), 400

            death_dt = datetime.strptime(new_date, '%Y-%m-%d')
            birth_dt = pick['birth_date']
            death_age = death_dt.year - birth_dt.year - ((death_dt.month, death_dt.day) < (birth_dt.month, birth_dt.day))
            points = max(0, 100 - death_age)

            cursor.execute("""
                UPDATE picks
                SET death_date = %s, death_age = %s, points = %s
                WHERE id = %s
            """, (new_date, death_age, points, pick_id))

        conn.commit()

        return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
