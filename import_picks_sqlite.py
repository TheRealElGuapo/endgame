import sqlite3

DB_PATH = 'deathpool.db'

# Participants
participants = ['Jim', 'Drew', 'Oost']

# Picks data - cleaned up from the provided lists
picks_data = {
    'Jim': [
        'Britney Spears',
        'Michael J. Fox',
        'Phil Collins',
        'Willie Nelson',
        'Ozzy Osbourne',
        'Volodymyr Zelensky',
        'Liza Minnelli',
        'Kanye West',
        'Bill Murray',
        'Iggy Pop',
        'Val Kilmer',
        'Dick Cheney',
        'Nicole Eggert',
        'Paul Simon',
        'Ananda Lewis',
        'Sally Struthers',
        'Ray Davies',
        'Robert Wagner',
        'Tori Spelling',
        'Robert Duvall',
        'Jon Voight',
        'Chris Evert',
        'Bruce Willis',
        'Ariana Grande',
        'Jimmy Swaggart',
        'Christina Applegate',
        'Lloyd Austin',
        'Sarah Ferguson',
        'Elon Musk',
        'Ben Affleck',
        'Lance Henriksen',
        'Lewis Capaldi',
        'Carl Bernstein',
        'Corey Feldman',
        'Victoria Jackson',
        'Jesse Jackson',
        'Yoko Ono',
        'Gary Busey',
        'Mitch McConnell',
        'Will Shortz',
        'Brian Wilson',
        'King Charles III',
        'Bam Margera',
        'Wink Martindale',
        'Justine Bateman',
        'Stevie Wonder',
        'Tom Brokaw',
        'Cybill Shepherd',
        'Rudy Giuliani',
        'Mary Lou Retton'
    ],
    'Drew': [
        'Bruce Willis',
        'Jack Nicholson',
        'Kanye West',
        'Bianca Censori',
        'Steve Bannon',
        'Mel Brooks',
        'Gene Hackman',
        'Chuck Grassley',
        'Justin Bieber',
        'Dick Van Dyke',
        'Imelda Marcos',
        'Madonna',
        'Yoko Ono',
        'Paul McCartney',
        'Elon Musk',
        'Cyndi Lauper',
        'Billy Idol',
        'Celine Dion',
        'Steve McMichael',
        'Christina Applegate',
        'Ian McKellen',
        'Johnny Depp',
        'Danny DeVito',
        'Caitlyn Jenner',
        'Paul Giamatti',
        'Lauren Boebert',
        'Mitch McConnell',
        'Cornel West',
        'Nancy Pelosi',
        'Joe Biden',
        'Hunter Biden',
        'Laura Loomer',
        'Elton John',
        'Pope Francis',
        'Donald Trump',
        'Shakira',
        'Phil Collins',
        'Rudy Giuliani',
        'Terry Bradshaw',
        'Lorne Michaels',
        'Tom Hanks',
        'Michael J Fox',
        'Dwight Clark',
        'Steve Gleason',
        'Harvey Weinstein',
        'Jim Kelly',
        'John Elway',
        'Randy Moss',
        'Bill Clinton',
        'Hulk Hogan'
    ],
    'Oost': [
        'Rupert Murdoch',
        'Justin Bieber',
        'Alan Alda',
        'Donald Trump',
        'Bam Margera',
        'Bruce Willis',
        'Vladimir Putin',
        'Michael J Fox',
        'Selma Blair',
        'Aung San Suu Kyi',
        'Samuel L Jackson',
        'Wendy Williams',
        'Kareem Abdul-Jabbar',
        'Sharon Osbourne',
        'Willie Nelson',
        'Harrison Ford',
        'Harvey Weinstein',
        'Gene Hackman',
        'Cara Delevingne',
        'Robert Plant',
        'Jon Voight',
        'Sonny Rollins',
        'Keith Richards',
        'Linda Ronstadt',
        'Bill Wyman',
        'Sam Neill',
        'Noam Chomsky',
        'Mary Lou Retton',
        'Celine Dion',
        'Clint Eastwood',
        'Robert Duvall',
        'John Cleese',
        'Terry Gilliam',
        'Francis Ford Coppola',
        'John Williams',
        'Drake',
        'Chuck Grassley',
        'Donald Trump Jr.',
        'Elon Musk',
        'Erik Jensen',
        'Yayoi Kusama',
        'Doc Severinsen',
        'Jack Nicholson',
        'Bill Cosby',
        'Elton John',
        'Jack Hanna',
        'Paul Schrader',
        'Victoria Jackson',
        "Roger O'Donnell",
        'Mitch McConnell'
    ]
}

def import_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM picks WHERE season_year = 2025")
    cursor.execute("DELETE FROM participants")

    # Insert participants
    for participant in participants:
        cursor.execute("INSERT INTO participants (name) VALUES (?)", (participant,))

    conn.commit()

    # Get participant IDs
    participant_ids = {}
    cursor.execute("SELECT id, name FROM participants")
    for row in cursor.fetchall():
        participant_ids[row[1]] = row[0]

    # Insert picks
    for participant, celebrities in picks_data.items():
        participant_id = participant_ids[participant]
        for celebrity in celebrities:
            cursor.execute("""
                INSERT INTO picks (participant_id, celebrity_name, season_year)
                VALUES (?, ?, 2025)
            """, (participant_id, celebrity))

    conn.commit()
    cursor.close()
    conn.close()

    print("✓ Data imported successfully!")
    print(f"  - Participants: {len(participants)}")
    print(f"  - Total picks: {sum(len(picks) for picks in picks_data.values())}")
    for participant, picks in picks_data.items():
        print(f"    - {participant}: {len(picks)} picks")

if __name__ == '__main__':
    import_data()
