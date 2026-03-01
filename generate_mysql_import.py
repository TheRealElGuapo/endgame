#!/usr/bin/env python3
"""
Converts SQLite JSON export to MySQL INSERT statements.
Usage: python3 generate_mysql_import.py data_export.json > import_data.sql
"""
import json
import sys
import re


def escape(val):
    if val is None:
        return 'NULL'
    if isinstance(val, bool):
        return '1' if val else '0'
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        val = re.sub(r'\s+', ' ', val).strip()
        val = val.replace('\\', '\\\\').replace("'", "\\'")
        return f"'{val}'"
    return f"'{val}'"


def insert_row(table, cols, row):
    vals = [escape(row.get(c)) for c in cols]
    return f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(vals)});"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_mysql_import.py data_export.json > import_data.sql",
              file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    print("-- MySQL import generated from SQLite export")
    print("SET FOREIGN_KEY_CHECKS=0;")
    print()

    print("-- participants")
    for row in data['participants']:
        print(insert_row('participants',
              ['id', 'name', 'username', 'password_hash', 'created_at'], row))
    print()

    print("-- season_config")
    for row in data['season_config']:
        print(insert_row('season_config',
              ['id', 'season_year', 'end_date', 'first_blood_winner_id', 'picks_locked', 'created_at'], row))
    print()

    print("-- picks")
    pk_cols = ['id', 'participant_id', 'celebrity_name', 'birth_date', 'age',
               'death_date', 'death_age', 'points', 'is_first_blood', 'season_year',
               'wikipedia_url', 'description', 'created_at', 'updated_at']
    for row in data['picks']:
        print(insert_row('picks', pk_cols, row))
    print()

    print("SET FOREIGN_KEY_CHECKS=1;")

    for tbl in ['participants', 'picks', 'season_config']:
        print(f"  {len(data[tbl])} rows from {tbl}", file=sys.stderr)


if __name__ == '__main__':
    main()
