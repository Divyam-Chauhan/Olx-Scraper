"""
SQLite DB handler for OLX rentals.
"""

import sqlite3
from datetime import datetime
from config import DB_PATH


def get_connection():
    """Return a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create the listings table if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price TEXT,
            url TEXT UNIQUE NOT NULL,
            seller_type TEXT,
            posted_date TEXT,
            bhk TEXT,
            furnishing TEXT,
            scraped_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def listing_exists(url):
    """Check if a URL already exists in DB."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM listings WHERE url = ?", (url,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def delete_listings(listing_ids):
    """Delete multiple listings by their IDs."""
    if not listing_ids:
        return
    conn = get_connection()
    cursor = conn.cursor()
    # Create the correct number of parameter placeholders
    placeholders = ','.join('?' * len(listing_ids))
    cursor.execute(f"DELETE FROM listings WHERE id IN ({placeholders})", listing_ids)
    conn.commit()
    conn.close()


def insert_listing(data):
    """Insert a new listing into the DB."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO listings
            (title, price, url, seller_type, posted_date, bhk, furnishing, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("title", ""),
            data.get("price", ""),
            data.get("url", ""),
            data.get("seller_type", ""),
            data.get("posted_date", ""),
            data.get("bhk", ""),
            data.get("furnishing", ""),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_listing_count():
    """Get total row count."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM listings")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_all_listings():
    """Retrieve all scraped listings from the database."""
    conn = get_connection()
    c = conn.cursor()
    # Fetch rows as dictionary-like objects
    c.row_factory = sqlite3.Row
    c.execute("SELECT * FROM listings ORDER BY scraped_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]
