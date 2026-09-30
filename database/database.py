import os
import sqlite3


# ============================================================
# DATABASE PATH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "fortnite.db"
)


# ============================================================
# CONNECTION
# ============================================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# CREATE DATABASE
# ============================================================

def create_database():

    connection = get_connection()

    cursor = connection.cursor()

    # ========================================================
    # PLAYERS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        )
    """)

    # ========================================================
    # USERS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ========================================================
    # FAVORITES
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            item_id TEXT NOT NULL,

            item_name TEXT,

            image_url TEXT,

            data_json TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(user_id, item_id)
        )
    """)

    # ========================================================
    # SHOP HISTORY
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            shop_date TEXT NOT NULL,

            item_id TEXT NOT NULL,

            item_name TEXT,

            image_url TEXT,

            data_json TEXT,

            saved_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(shop_date, item_id)
        )
    """)

    # ========================================================
    # NOTIFICATION LOG
    #
    # Tiene traccia delle notifiche già inviate.
    #
    # In questo modo la stessa skin non genera
    # 10 email durante lo stesso giorno.
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            item_id TEXT NOT NULL,

            shop_date TEXT NOT NULL,

            item_name TEXT,

            sent_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(user_id, item_id, shop_date)
        )
    """)

    # ========================================================
    # NOTIFICATION SETTINGS
    #
    # Una riga per utente.
    #
    # enabled = 1 -> notifiche attive
    # enabled = 0 -> notifiche disattivate
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_settings (
            user_id INTEGER PRIMARY KEY,

            enabled INTEGER NOT NULL
                DEFAULT 1,

            updated_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()

    connection.close()
