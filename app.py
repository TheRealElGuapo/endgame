from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import requests
import re
from contextlib import contextmanager
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'deathpool-dev-key-change-in-production')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, name, username):
        self.id = id
        self.name = name
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, username FROM participants WHERE id = ?", (int(user_id),))
        row = cursor.fetchone()
        if row:
            return User(row['id'], row['name'], row['username'])
        return None

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
            return None

        data = response.json()
        print(f"Search results: {len(data.get('query', {}).get('search', []))} found")

        if not data.get('query', {}).get('search'):
            return None

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
            return None

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM participants WHERE username = ?", (username,))
            row = cursor.fetchone()
        if row and row.get('password_hash') and check_password_hash(row['password_hash'], password):
            user = User(row['id'], row['name'], row['username'])
            login_user(user, remember=True)
            return redirect(request.args.get('next') or url_for('index'))
        error = 'Invalid username or password'
    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    """Main dashboard showing leaderboard and all picks"""
    season_year = int(request.args.get('season', datetime.now().year))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get all available seasons
        cursor.execute("SELECT season_year FROM season_config ORDER BY season_year DESC")
        available_seasons = [row['season_year'] for row in cursor.fetchall()]

        # Auto-create season config if it doesn't exist
        if season_year not in available_seasons:
            cursor.execute("""
                INSERT INTO season_config (season_year, end_date)
                VALUES (?, ?)
            """, (season_year, f'{season_year}-12-31 23:59:59'))
            conn.commit()
            available_seasons.insert(0, season_year)

        # Get current season config
        cursor.execute("SELECT * FROM season_config WHERE season_year = ?", (season_year,))
        season = cursor.fetchone()

        # Calculate time remaining
        end_date = datetime.strptime(season['end_date'], '%Y-%m-%d %H:%M:%S')
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
            LEFT JOIN picks pk ON p.id = pk.participant_id AND pk.season_year = ?
            GROUP BY p.id, p.name
            ORDER BY total_points DESC, deaths_count DESC
        """, (season_year,))
        leaderboard = cursor.fetchall()

        # Get first blood info (all picks with the earliest death date - handles ties)
        cursor.execute("""
            SELECT p.name, pk.celebrity_name, pk.death_date, pk.death_age, pk.points
            FROM picks pk
            JOIN participants p ON pk.participant_id = p.id
            WHERE pk.death_date = (
                SELECT MIN(death_date)
                FROM picks
                WHERE death_date IS NOT NULL AND season_year = ?
            )
            AND pk.season_year = ?
            ORDER BY p.name
        """, (season_year, season_year))
        first_blood_picks = cursor.fetchall()

        # Get all picks with details
        cursor.execute("""
            SELECT
                pk.*,
                p.name as participant_name
            FROM picks pk
            JOIN participants p ON pk.participant_id = p.id
            WHERE pk.season_year = ?
            ORDER BY p.name, pk.celebrity_name
        """, (season_year,))
        all_picks = cursor.fetchall()

        # Determine first blood picks (all with earliest death date) and mark them
        first_blood_pick_ids = set()
        if first_blood_picks:
            earliest_death_date = first_blood_picks[0]['death_date']
            first_blood_pick_ids = {
                pick['id'] for pick in all_picks
                if pick['death_date'] == earliest_death_date
            }

        # Group picks by participant and mark first blood
        # For unlocked seasons, only show each user their own picks (draft privacy)
        picks_locked = bool(season.get('picks_locked', 0))
        picks_by_participant = {}
        for pick in all_picks:
            pick['is_first_blood'] = (pick['id'] in first_blood_pick_ids)
            participant = pick['participant_name']
            if not picks_locked:
                # Draft mode: only show your own picks
                if not current_user.is_authenticated or pick['participant_id'] != current_user.id:
                    continue
            if participant not in picks_by_participant:
                picks_by_participant[participant] = []
            picks_by_participant[participant].append(pick)

        # Get participant IDs for the import button
        cursor.execute("SELECT id, name FROM participants ORDER BY name")
        participants = cursor.fetchall()

        season_start = f'{season_year}-01-01'

        # Compute fun stats per participant
        stats_by_participant = {}
        for p in participants:
            p_picks = picks_by_participant.get(p['name'], [])
            picks_with_age = [pk for pk in p_picks if pk.get('age')]
            avg_age = round(sum(pk['age'] for pk in picks_with_age) / len(picks_with_age), 1) if picks_with_age else None
            oldest = max(picks_with_age, key=lambda x: x['age']) if picks_with_age else None
            youngest = min(picks_with_age, key=lambda x: x['age']) if picks_with_age else None
            stats_by_participant[p['name']] = {
                'avg_age': avg_age,
                'oldest': oldest,
                'youngest': youngest,
                'picks_with_age_count': len(picks_with_age),
            }

        return render_template('index.html',
                             leaderboard=leaderboard,
                             first_blood_picks=first_blood_picks,
                             picks_by_participant=picks_by_participant,
                             days_remaining=days_remaining,
                             hours_remaining=hours_remaining,
                             season_end=end_date.strftime('%B %d, %Y at %I:%M:%S %p'),
                             season_start=season_start,
                             season_year=season_year,
                             available_seasons=available_seasons,
                             participants=participants,
                             stats_by_participant=stats_by_participant,
                             picks_locked=picks_locked)

@app.route('/lookup_age/<int:pick_id>')
@login_required
def lookup_age(pick_id):
    """Look up age for a specific pick"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT celebrity_name, participant_id, season_year FROM picks WHERE id = ?", (pick_id,))
        pick = cursor.fetchone()

        if not pick:
            return jsonify({'error': 'Pick not found'}), 404

        if pick['participant_id'] != current_user.id:
            return jsonify({'error': 'Not your pick'}), 403

        result = get_wikipedia_age(pick['celebrity_name'])

        if result and result['age'] is not None:
            if result['death_date']:
                points = max(0, 100 - result['death_age'])

                cursor.execute("""
                    SELECT COUNT(*) as death_count
                    FROM picks
                    WHERE season_year = ? AND death_date IS NOT NULL
                """, (pick['season_year'],))
                is_first_blood = (cursor.fetchone()['death_count'] == 0)

                cursor.execute("""
                    UPDATE picks
                    SET age = ?, birth_date = ?, death_date = ?, death_age = ?,
                        points = ?, is_first_blood = ?, wikipedia_url = ?, description = ?
                    WHERE id = ?
                """, (result['age'], result['birth_date'], result['death_date'],
                      result['death_age'], points, is_first_blood, result['wiki_url'], result['description'], pick_id))

                if is_first_blood:
                    cursor.execute("""
                        UPDATE season_config
                        SET first_blood_winner_id = ?
                        WHERE season_year = ?
                    """, (pick['participant_id'], pick['season_year']))
            else:
                cursor.execute("""
                    UPDATE picks
                    SET age = ?, birth_date = ?, wikipedia_url = ?, description = ?
                    WHERE id = ?
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
@login_required
def mark_death(pick_id):
    """Mark a celebrity as deceased and calculate points"""
    death_date = request.form.get('death_date')
    season_year = int(request.form.get('season_year', datetime.now().year))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM picks WHERE id = ?", (pick_id,))
        pick = cursor.fetchone()

        if not pick:
            return jsonify({'error': 'Pick not found'}), 404

        if pick['participant_id'] != current_user.id:
            return redirect(url_for('index', season=season_year))

        # Calculate death age and points
        death_dt = datetime.strptime(death_date, '%Y-%m-%d')

        if pick['birth_date']:
            birth_dt = datetime.strptime(str(pick['birth_date']), '%Y-%m-%d')
            death_age = death_dt.year - birth_dt.year - ((death_dt.month, death_dt.day) < (birth_dt.month, birth_dt.day))
        else:
            death_age = pick['age'] if pick['age'] else 0

        points = max(0, 100 - death_age)

        # Check if this is the first death of the season (First Blood)
        cursor.execute("""
            SELECT COUNT(*) as death_count
            FROM picks
            WHERE season_year = ? AND death_date IS NOT NULL
        """, (pick['season_year'],))
        result = cursor.fetchone()
        is_first_blood = (result['death_count'] == 0)

        cursor.execute("""
            UPDATE picks
            SET death_date = ?, death_age = ?, points = ?, is_first_blood = ?
            WHERE id = ?
        """, (death_date, death_age, points, is_first_blood, pick_id))

        if is_first_blood:
            cursor.execute("""
                UPDATE season_config
                SET first_blood_winner_id = ?
                WHERE season_year = ?
            """, (pick['participant_id'], pick['season_year']))

        conn.commit()

        return redirect(url_for('index', season=season_year))

@app.route('/unmark_death/<int:pick_id>', methods=['POST'])
@login_required
def unmark_death(pick_id):
    """Remove death marking from a pick"""
    season_year = int(request.form.get('season_year', datetime.now().year))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT is_first_blood, season_year, participant_id FROM picks WHERE id = ?", (pick_id,))
        pick = cursor.fetchone()

        if pick and pick['participant_id'] != current_user.id:
            return redirect(url_for('index', season=season_year))

        cursor.execute("""
            UPDATE picks
            SET death_date = NULL, death_age = NULL, points = 0, is_first_blood = 0
            WHERE id = ?
        """, (pick_id,))

        if pick and pick['is_first_blood']:
            cursor.execute("""
                UPDATE season_config
                SET first_blood_winner_id = NULL
                WHERE season_year = ?
            """, (pick['season_year'],))

        conn.commit()

        return redirect(url_for('index', season=season_year))

@app.route('/add_pick', methods=['POST'])
@login_required
def add_pick():
    """Add a new pick for a participant"""
    participant_id = int(request.form.get('participant_id'))
    celebrity_name = request.form.get('celebrity_name')
    season_year = int(request.form.get('season_year', datetime.now().year))

    if participant_id != current_user.id:
        return redirect(url_for('index', season=season_year))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO picks (participant_id, celebrity_name, season_year)
            VALUES (?, ?, ?)
        """, (participant_id, celebrity_name, season_year))

        conn.commit()

        return redirect(url_for('index', season=season_year))

@app.route('/delete_pick/<int:pick_id>', methods=['POST'])
@login_required
def delete_pick(pick_id):
    """Delete a pick"""
    season_year = int(request.form.get('season_year', datetime.now().year))

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT participant_id FROM picks WHERE id = ?", (pick_id,))
        pick = cursor.fetchone()
        if not pick or pick['participant_id'] != current_user.id:
            return redirect(url_for('index', season=season_year))
        cursor.execute("DELETE FROM picks WHERE id = ?", (pick_id,))
        conn.commit()

        return redirect(url_for('index', season=season_year))

@app.route('/import_from_last_year', methods=['POST'])
@login_required
def import_from_last_year():
    """Import living picks from the previous season for a participant"""
    participant_id = int(request.form.get('participant_id'))
    season_year = int(request.form.get('season_year', datetime.now().year))

    if participant_id != current_user.id:
        return redirect(url_for('index', season=season_year))
    last_year = season_year - 1

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get all living picks from last season for this participant
        cursor.execute("""
            SELECT celebrity_name, age, birth_date, wikipedia_url, description
            FROM picks
            WHERE participant_id = ? AND season_year = ? AND death_date IS NULL
        """, (participant_id, last_year))
        living_picks = cursor.fetchall()

        # Get names already picked this season to avoid duplicates
        cursor.execute("""
            SELECT celebrity_name FROM picks
            WHERE participant_id = ? AND season_year = ?
        """, (participant_id, season_year))
        existing = {row['celebrity_name'] for row in cursor.fetchall()}

        imported = 0
        for pick in living_picks:
            if pick['celebrity_name'] not in existing:
                cursor.execute("""
                    INSERT INTO picks (participant_id, celebrity_name, season_year, age, birth_date, wikipedia_url, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (participant_id, pick['celebrity_name'], season_year,
                      pick['age'], pick['birth_date'], pick['wikipedia_url'], pick['description']))
                imported += 1

        conn.commit()
        print(f"Imported {imported} picks from {last_year} for participant {participant_id}")

        return redirect(url_for('index', season=season_year))

@app.route('/update_date/<int:pick_id>', methods=['POST'])
@login_required
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
            cursor.execute("SELECT * FROM picks WHERE id = ?", (pick_id,))
            pick = cursor.fetchone()

            if not pick or pick['participant_id'] != current_user.id:
                return jsonify({'success': False, 'error': 'Not your pick'}), 403

            birth_dt = datetime.strptime(new_date, '%Y-%m-%d')

            if pick['death_date']:
                death_dt = datetime.strptime(str(pick['death_date']), '%Y-%m-%d')
                death_age = death_dt.year - birth_dt.year - ((death_dt.month, death_dt.day) < (birth_dt.month, birth_dt.day))
                age = death_age
                points = max(0, 100 - death_age)

                cursor.execute("""
                    UPDATE picks
                    SET birth_date = ?, age = ?, death_age = ?, points = ?
                    WHERE id = ?
                """, (new_date, age, death_age, points, pick_id))
            else:
                today = datetime.now()
                age = today.year - birth_dt.year - ((today.month, today.day) < (birth_dt.month, birth_dt.day))

                cursor.execute("""
                    UPDATE picks
                    SET birth_date = ?, age = ?
                    WHERE id = ?
                """, (new_date, age, pick_id))

        elif date_type == 'death':
            cursor.execute("SELECT * FROM picks WHERE id = ?", (pick_id,))
            pick = cursor.fetchone()

            if not pick or pick['participant_id'] != current_user.id:
                return jsonify({'success': False, 'error': 'Not your pick'}), 403

            if not pick['birth_date']:
                return jsonify({'success': False, 'error': 'Cannot set death date without birth date'}), 400

            death_dt = datetime.strptime(new_date, '%Y-%m-%d')
            birth_dt = datetime.strptime(str(pick['birth_date']), '%Y-%m-%d')
            death_age = death_dt.year - birth_dt.year - ((death_dt.month, death_dt.day) < (birth_dt.month, birth_dt.day))
            points = max(0, 100 - death_age)

            cursor.execute("""
                UPDATE picks
                SET death_date = ?, death_age = ?, points = ?
                WHERE id = ?
            """, (new_date, death_age, points, pick_id))

        conn.commit()

        return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
