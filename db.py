import sqlite3
import os
import logging
from typing import List, Optional, Tuple, Dict

# Lokasi database
DB_DIR = os.path.join(os.path.dirname(__file__), 'data')
DB_PATH = os.path.join(DB_DIR, 'users.db')
os.makedirs(DB_DIR, exist_ok=True)

def get_connection() -> sqlite3.Connection:
    """Buka koneksi SQLite ke database pengguna."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# Inisialisasi skema database
with get_connection() as conn:
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT
        );
        CREATE TABLE IF NOT EXISTS banned_users (
            id INTEGER PRIMARY KEY,
            reason TEXT DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT
        );
        CREATE TABLE IF NOT EXISTS hashtag_stats (
            hashtag TEXT PRIMARY KEY,
            count INTEGER
        );
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS pending_menfess (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content_type TEXT,
            text TEXT,
            file_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER,
            message_text TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    # Migrasi: tambah kolom reason ke banned_users jika belum ada
    try:
        conn.execute("ALTER TABLE banned_users ADD COLUMN reason TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # Kolom sudah ada
    conn.commit()

# === USERS ===

def add_user(user_id: int, username: Optional[str]) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users (id, username) VALUES (?, ?)",
            (user_id, username)
        )
        conn.commit()

def get_user_by_id(user_id: int) -> Optional[Dict[str, Optional[str]]]:
    with get_connection() as conn:
        row = conn.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
        return {"id": row[0], "username": row[1]} if row else None


def get_user_by_username(username: str) -> Optional[Dict[str, Optional[str]]]:
    """
    Cari user berdasarkan username (tanpa / dengan '@').
    Pencarian tidak case-sensitive.
    """
    username = username.lstrip("@")
    if not username:
        return None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username FROM users WHERE LOWER(username) = LOWER(?)",
            (username,),
        ).fetchone()
        return {"id": row[0], "username": row[1]} if row else None

def get_username_by_id(user_id: int) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        return row[0] if row else None

def get_all_users() -> List[int]:
    with get_connection() as conn:
        return [row[0] for row in conn.execute("SELECT id FROM users").fetchall()]

def get_user_post_count(user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM posts WHERE user_id = ?", (user_id,)).fetchone()
        return row[0] if row else 0

# === BANNED USERS ===

def ban_user(user_id: int, reason: Optional[str] = None) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO banned_users (id, reason) VALUES (?, ?)",
            (user_id, reason)
        )
        conn.commit()

def unban_user(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM banned_users WHERE id = ?", (user_id,))
        conn.commit()

def is_banned(user_id: int) -> bool:
    with get_connection() as conn:
        return conn.execute("SELECT 1 FROM banned_users WHERE id = ?", (user_id,)).fetchone() is not None

def get_ban_reason(user_id: int) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute("SELECT reason FROM banned_users WHERE id = ?", (user_id,)).fetchone()
        return row[0] if row else None

def get_all_banned_users() -> List[Tuple[int, Optional[str]]]:
    with get_connection() as conn:
        return conn.execute("SELECT id, reason FROM banned_users").fetchall()

def clear_banlist() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM banned_users")
        conn.commit()

# === POSTS ===

def log_post(user_id: int, text: str) -> None:
    with get_connection() as conn:
        conn.execute("INSERT INTO posts (user_id, text) VALUES (?, ?)", (user_id, text))
        conn.commit()

def latest_post(user_id: int) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT text FROM posts WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,)
        ).fetchone()
        return row[0] if row else None

def get_last_posts(limit: int = 10) -> List[Tuple[int, str]]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT user_id, text FROM posts ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()[::-1]


def get_posts_by_user(user_id: int, limit: int = 10) -> List[Tuple[int, str]]:
    """
    Ambil riwayat postingan milik satu user (urut terbaru -> lama).
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, text FROM posts WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return rows

# === HASHTAGS ===

def count_hashtags(text: str) -> None:
    """Perbarui statistik hashtag berdasarkan teks."""
    words = text.lower().split()
    with get_connection() as conn:
        for word in words:
            if word.startswith("#"):
                hashtag = word.strip()
                row = conn.execute("SELECT count FROM hashtag_stats WHERE hashtag = ?", (hashtag,)).fetchone()
                if row:
                    conn.execute("UPDATE hashtag_stats SET count = count + 1 WHERE hashtag = ?", (hashtag,))
                else:
                    conn.execute("INSERT INTO hashtag_stats (hashtag, count) VALUES (?, 1)", (hashtag,))
        conn.commit()

def get_top_hashtags(n: int = 5) -> List[Tuple[str, int]]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT hashtag, count FROM hashtag_stats ORDER BY count DESC LIMIT ?",
            (n,)
        ).fetchall()

# === ADMINS ===

def add_admin_id(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO admins (id) VALUES (?)", (user_id,))
        conn.commit()

def remove_admin_id(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM admins WHERE id = ?", (user_id,))
        conn.commit()

def get_admin_ids() -> List[int]:
    with get_connection() as conn:
        return [row[0] for row in conn.execute("SELECT id FROM admins").fetchall()]

def get_all_admins() -> List[Dict[str, Optional[str]]]:
    with get_connection() as conn:
        return [
            {"id": row[0], "username": row[1]}
            for row in conn.execute(
                "SELECT a.id, u.username FROM admins a LEFT JOIN users u ON a.id = u.id"
            ).fetchall()
        ]

# === PENDING MENFESS (Approval Mode) ===

def add_pending_menfess(user_id: int, content_type: str, text: str, file_id: Optional[str] = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO pending_menfess (user_id, content_type, text, file_id) VALUES (?, ?, ?, ?)",
            (user_id, content_type, text, file_id)
        )
        conn.commit()
        return cursor.lastrowid

def get_pending_menfess_list(limit: int = 10) -> List[Dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, user_id, content_type, text, file_id, created_at FROM pending_menfess ORDER BY id ASC LIMIT ?",
            (limit,)
        ).fetchall()
        return [
            {"id": r[0], "user_id": r[1], "content_type": r[2], "text": r[3], "file_id": r[4], "created_at": r[5]}
            for r in rows
        ]

def get_pending_menfess_by_id(menfess_id: int) -> Optional[Dict]:
    with get_connection() as conn:
        r = conn.execute(
            "SELECT id, user_id, content_type, text, file_id, created_at FROM pending_menfess WHERE id = ?",
            (menfess_id,)
        ).fetchone()
        if r:
            return {"id": r[0], "user_id": r[1], "content_type": r[2], "text": r[3], "file_id": r[4], "created_at": r[5]}
        return None

def remove_pending_menfess(menfess_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM pending_menfess WHERE id = ?", (menfess_id,))
        conn.commit()

# === REPORTS ===

def add_report(reporter_id: int, message_text: str, reason: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO reports (reporter_id, message_text, reason) VALUES (?, ?, ?)",
            (reporter_id, message_text, reason)
        )
        conn.commit()
        return cursor.lastrowid

def get_reports(limit: int = 10) -> List[Dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, reporter_id, message_text, reason, created_at FROM reports ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [
            {"id": r[0], "reporter_id": r[1], "message_text": r[2], "reason": r[3], "created_at": r[4]}
            for r in rows
        ]

def clear_reports() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM reports")
        conn.commit()
