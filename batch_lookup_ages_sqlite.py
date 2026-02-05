import sqlite3
import requests
import re
from datetime import datetime
import time

DB_PATH = 'deathpool.db'

def dict_factory(cursor, row):
    """Convert database rows to dictionaries"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_wikipedia_age(celebrity_name):
    """Fetch age from Wikipedia using their API"""
    try:
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

        response = requests.get(search_url, params=search_params, headers=headers, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()

        if not data.get('query', {}).get('search'):
            return None

        # Get the page content and description
        page_title = data['query']['search'][0]['title']
        page_id = data['query']['search'][0]['pageid']

        content_params = {
            'action': 'query',
            'prop': 'revisions|description',
            'titles': page_title,
            'rvprop': 'content',
            'format': 'json',
            'rvslots': 'main'
        }

        response = requests.get(search_url, params=content_params, headers=headers, timeout=10)

        if response.status_code != 200:
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

        return {
            'age': age,
            'birth_date': birth_date,
            'death_date': death_date,
            'death_age': death_age,
            'wiki_url': wiki_url,
            'description': description
        }
    except Exception as e:
        print(f"Error for {celebrity_name}: {e}")
        return None

def batch_lookup():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    # Get all picks without age
    cursor.execute("""
        SELECT id, celebrity_name
        FROM picks
        WHERE season_year = 2025 AND (age IS NULL OR birth_date IS NULL)
        ORDER BY celebrity_name
    """)

    picks = cursor.fetchall()
    total = len(picks)

    print(f"\nFound {total} celebrities without age data")
    print("=" * 60)

    success = 0
    failed = 0

    for i, pick in enumerate(picks, 1):
        pick_id = pick['id']
        celebrity = pick['celebrity_name']

        print(f"\n[{i}/{total}] Looking up: {celebrity}")

        result = get_wikipedia_age(celebrity)

        if result and result['age'] is not None:
            if result['death_date']:
                # Calculate points for deceased person
                points = max(0, 100 - result['death_age'])

                # Check if this is first blood
                cursor.execute("""
                    SELECT COUNT(*) as death_count
                    FROM picks
                    WHERE season_year = 2025 AND death_date IS NOT NULL
                """)
                is_first_blood = 1 if (cursor.fetchone()['death_count'] == 0) else 0

                cursor.execute("""
                    UPDATE picks
                    SET age = ?, birth_date = ?, death_date = ?, death_age = ?, points = ?, is_first_blood = ?, description = ?, wikipedia_url = ?
                    WHERE id = ?
                """, (result['age'], result['birth_date'], result['death_date'], result['death_age'], points, is_first_blood, result['description'], result['wiki_url'], pick_id))

                print(f"  ✓ Found: Age {result['age']}, Born {result['birth_date']}")
                print(f"  💀 DECEASED: Died {result['death_date']}, Age {result['death_age']}, {points} points")
            else:
                cursor.execute("""
                    UPDATE picks
                    SET age = ?, birth_date = ?, description = ?, wikipedia_url = ?
                    WHERE id = ?
                """, (result['age'], result['birth_date'], result['description'], result['wiki_url'], pick_id))
                print(f"  ✓ Found: Age {result['age']}, Born {result['birth_date']}")

            conn.commit()
            success += 1
        else:
            print(f"  ✗ Not found")
            failed += 1

        # Be nice to Wikipedia - wait between requests
        if i < total:
            time.sleep(0.5)

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print(f"Completed: {success} found, {failed} not found")

if __name__ == '__main__':
    batch_lookup()
