import sqlite3


def create_database():
    connection = sqlite3.connect("fortnite.db")

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        )
    """)

    connection.commit()
    connection.close()
