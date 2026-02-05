#!/usr/bin/env python3
"""Export data from local MySQL database to SQLite format"""
import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '14231423',
    'database': 'deathpool'
}

def export_to_sql():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    # Get all participants
    cursor.execute("SELECT * FROM participants ORDER BY id")
    participants = cursor.fetchall()

    # Get all picks
    cursor.execute("SELECT * FROM picks ORDER BY id")
    picks = cursor.fetchall()

    cursor.close()
    conn.close()

    # Generate SQLite INSERT statements
    with open('data_export.sql', 'w') as f:
        f.write("-- Data export from MySQL\n\n")

        # Clear existing data
        f.write("DELETE FROM picks WHERE season_year = 2025;\n")
        f.write("DELETE FROM participants;\n\n")

        # Insert participants
        f.write("-- Participants\n")
        for p in participants:
            f.write(f"INSERT INTO participants (id, name) VALUES ({p['id']}, '{p['name']}');\n")

        f.write("\n-- Picks\n")
        for pick in picks:
            # Build the INSERT statement with only non-null values
            columns = ['id', 'participant_id', 'celebrity_name', 'season_year']

            # Escape single quotes in celebrity name
            celeb_name = pick['celebrity_name'].replace("'", "''") if pick['celebrity_name'] else None

            values = [
                str(pick['id']),
                str(pick['participant_id']),
                f"'{celeb_name}'" if celeb_name else 'NULL',
                str(pick['season_year'])
            ]

            if pick['age'] is not None:
                columns.append('age')
                values.append(str(pick['age']))

            if pick['birth_date'] is not None:
                columns.append('birth_date')
                values.append(f"'{pick['birth_date']}'")

            if pick['death_date'] is not None:
                columns.append('death_date')
                values.append(f"'{pick['death_date']}'")

            if pick['death_age'] is not None:
                columns.append('death_age')
                values.append(str(pick['death_age']))

            if pick['points'] is not None and pick['points'] > 0:
                columns.append('points')
                values.append(str(pick['points']))

            if pick['is_first_blood']:
                columns.append('is_first_blood')
                values.append('1')

            if pick.get('wikipedia_url'):
                columns.append('wikipedia_url')
                values.append(f"'{pick['wikipedia_url']}'")

            if pick.get('description'):
                columns.append('description')
                # Escape single quotes
                desc = pick['description'].replace("'", "''") if pick['description'] else ''
                values.append(f"'{desc}'")

            f.write(f"INSERT INTO picks ({', '.join(columns)}) VALUES ({', '.join(values)});\n")

    print(f"✓ Exported {len(participants)} participants and {len(picks)} picks to data_export.sql")
    print(f"\nNow:")
    print(f"1. git add data_export.sql && git commit -m 'Add data export' && git push")
    print(f"2. On PythonAnywhere: cd ~/endgame && git pull")
    print(f"3. sqlite3 deathpool.db < data_export.sql")

if __name__ == '__main__':
    export_to_sql()
