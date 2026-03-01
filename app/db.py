"""SQLite persistence for uploads and transactions."""

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from app.config import DB_PATH
from app.models import Transaction


def _init_db():
    """Create tables if not exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            month TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id INTEGER,
            date TEXT NOT NULL,
            merchant_raw TEXT,
            merchant TEXT,
            category TEXT,
            amount REAL NOT NULL,
            currency TEXT,
            direction TEXT,
            balance REAL,
            confidence REAL,
            FOREIGN KEY (upload_id) REFERENCES uploads(id)
        )
    """)
    conn.commit()
    conn.close()


def save_upload(filename: str, file_path: str, month: str = "") -> int:
    """Save upload metadata, return upload_id."""
    _init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO uploads (filename, file_path, month) VALUES (?, ?, ?)",
        (filename, str(file_path), month),
    )
    upload_id = cur.lastrowid
    conn.commit()
    conn.close()
    return upload_id or 0


def save_transactions(upload_id: int, transactions: list[Transaction]):
    """Save transactions for an upload."""
    conn = sqlite3.connect(DB_PATH)
    for t in transactions:
        conn.execute(
            """INSERT INTO transactions (upload_id, date, merchant_raw, merchant, category, amount, currency, direction, balance, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                upload_id,
                t.date.isoformat(),
                t.merchant_raw,
                t.merchant,
                t.category,
                t.amount,
                t.currency,
                t.direction,
                t.balance,
                t.confidence,
            ),
        )
    conn.commit()
    conn.close()


def get_upload(upload_id: int) -> Optional[dict]:
    """Get upload metadata."""
    _init_db()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id, filename, file_path, month, created_at FROM uploads WHERE id = ?",
        (upload_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "filename": row[1],
        "file_path": row[2],
        "month": row[3],
        "created_at": row[4],
    }


def get_transactions(upload_id: int) -> list[Transaction]:
    """Load transactions for an upload."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """SELECT date, merchant_raw, merchant, category, amount, currency, direction, balance, confidence
           FROM transactions WHERE upload_id = ? ORDER BY date""",
        (upload_id,),
    ).fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append(
            Transaction(
                date=datetime.strptime(r[0], "%Y-%m-%d").date(),
                merchant_raw=r[1] or "",
                merchant=r[2] or "",
                category=r[3] or "Other",
                amount=r[4],
                currency=r[5] or "TRY",
                direction=r[6] or "expense",
                balance=r[7],
                confidence=r[8] or 1.0,
            )
        )
    return result
