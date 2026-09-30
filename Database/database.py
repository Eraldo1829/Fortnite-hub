import os
import sqlite3


# =========================
# DATABASE PATH
# =========================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "fortnite.db"
)


# =========================
# CONNECTION
# =========================

def get_connection():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


# =========================
# CREATE DATABASE
# =========================

def create_database():

    connection = get_connection()

    cursor = connection.cursor()


    # =========================
    # PLAYERS
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL

        )
    """)


    # =========================
    # USERS
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password_hash TEXT NOT NULL,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP

        )
    """)


    connection.commit()

    connection.close()
