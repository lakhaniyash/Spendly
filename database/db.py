import sqlite3
from flask import g

DATABASE = 'expense_tracker.db'


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT    NOT NULL,
            email          TEXT    UNIQUE NOT NULL,
            password_hash  TEXT    NOT NULL,
            role           TEXT    NOT NULL DEFAULT 'user'
                           CHECK(role IN ('user', 'admin')),
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            title       TEXT    NOT NULL,
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            note        TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    db.commit()


def seed_db():
    from werkzeug.security import generate_password_hash
    db = get_db()
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return
    db.executemany(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        [
            ("Admin", "admin@spendly.com", generate_password_hash("admin123"), "admin"),
            ("Nitish Kumar", "nitish@example.com", generate_password_hash("user123"), "user"),
        ]
    )
    user_id = db.execute(
        "SELECT id FROM users WHERE email = ?", ("nitish@example.com",)
    ).fetchone()["id"]
    db.executemany(
        "INSERT INTO expenses (user_id, title, amount, category, date, note) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (user_id, "Weekly groceries", 1250.00, "Food", "2026-06-01", ""),
            (user_id, "Electricity bill", 2100.00, "Utilities", "2026-06-05", ""),
            (user_id, "Movie tickets", 450.00, "Entertainment", "2026-06-10", "Film with friends"),
            (user_id, "Fuel", 800.00, "Transport", "2026-06-15", ""),
            (user_id, "Restaurant lunch", 1800.00, "Food", "2026-06-20", "Team lunch"),
        ]
    )
    db.commit()
