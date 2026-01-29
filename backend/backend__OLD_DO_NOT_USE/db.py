# backend/db.py
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(os.getenv("RAYBURN_DB_PATH", Path(__file__).parent / "data" / "rayburn.db"))

BAIT_TAXONOMY = [
    # slug, label
    ("soft_plastics", "Soft Plastics"),
    ("jigs", "Jigs"),
    ("worms", "Worms"),
    ("creature_baits", "Creature Baits"),
    ("swimbaits", "Swimbaits"),
    ("spinnerbaits", "Spinnerbaits"),
    ("chatterbaits", "Chatterbaits / Bladed Jigs"),
    ("crankbaits", "Crankbaits"),
    ("jerkbaits", "Jerkbaits"),
    ("topwater", "Topwater"),
    ("frogs", "Frogs"),
    ("spoons", "Spoons"),
    ("drop_shot", "Drop Shot"),
    ("carolina_rig", "Carolina Rig"),
    ("texas_rig", "Texas Rig"),
    ("ned_rig", "Ned Rig"),
    ("umbrella_rig", "Umbrella Rig (A-Rig)"),
    ("live_bait", "Live Bait"),
    ("other", "Other / Unclassified"),
]
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

def table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
    return any(r[1] == column for r in rows)

def ensure_bait_taxonomy(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bait_categories (
            slug TEXT PRIMARY KEY,
            label TEXT NOT NULL
        );
        """
    )

    # Seed / upsert taxonomy
    conn.executemany(
        """
        INSERT INTO bait_categories(slug, label)
        VALUES (?, ?)
        ON CONFLICT(slug) DO UPDATE SET label=excluded.label;
        """,
        BAIT_TAXONOMY,
    )

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = connect()
    conn.execute("PRAGMA foreign_keys = ON;")

    # Core tables
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            channel TEXT,
            published_at TEXT,
            url TEXT
        );

        CREATE TABLE IF NOT EXISTS baits (
            bait_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category_slug TEXT,             -- NEW: taxonomy slug (FK)
            confidence_default INTEGER DEFAULT 75,
            FOREIGN KEY (category_slug) REFERENCES bait_categories(slug)
        );

        CREATE TABLE IF NOT EXISTS bait_hits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            bait_id INTEGER NOT NULL,
            confidence INTEGER,
            source TEXT DEFAULT 'whisper',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE,
            FOREIGN KEY (bait_id) REFERENCES baits(bait_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_bait_hits_video
            ON bait_hits(video_id);

        CREATE INDEX IF NOT EXISTS idx_bait_hits_bait
            ON bait_hits(bait_id);
        """
    )

    # Taxonomy table + seed
    ensure_bait_taxonomy(conn)

    # If you already had an older `baits` table without category_slug, add it safely
    # (SQLite doesn't support "ADD COLUMN IF NOT EXISTS", so we check PRAGMA table_info)
    if not table_has_column(conn, "baits", "category_slug"):
        conn.execute("ALTER TABLE baits ADD COLUMN category_slug TEXT;")

    conn.commit()
    conn.close()

def upsert_bait(conn: sqlite3.Connection, name: str, category_slug: Optional[str] = None) -> int:
    # Normalize
    name_clean = (name or "").strip()
    if not name_clean:
        raise ValueError("bait name required")

    if category_slug:
        # Validate taxonomy slug exists; if not, fall back to 'other'
        row = conn.execute(
            "SELECT slug FROM bait_categories WHERE slug = ?",
            (category_slug,),
        ).fetchone()
        if not row:
            category_slug = "other"

    conn.execute(
        """
        INSERT INTO baits(name, category_slug)
        VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET
            category_slug = COALESCE(excluded.category_slug, baits.category_slug)
        """,
        (name_clean, category_slug),
    )

    bait_id = conn.execute("SELECT bait_id FROM baits WHERE name = ?", (name_clean,)).fetchone()[0]
    return int(bait_id)


def set_bait_category(conn: sqlite3.Connection, bait_name: str, category_slug: str) -> None:
    if not category_slug:
        category_slug = "other"
    conn.execute(
        """
        UPDATE baits
        SET category_slug = ?
        WHERE name = ?
        """,
        (category_slug, bait_name.strip()),
    )



def upsert_video(conn: sqlite3.Connection, v: dict) -> None:
    video_id = v.get("videoId") or v.get("video_id") or v.get("id")
    if not video_id:
        return

    conn.execute(
        """
        INSERT INTO videos (video_id, title, url, channel, published_at, thumbnail, raw_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
          title=excluded.title,
          url=excluded.url,
          channel=excluded.channel,
          published_at=excluded.published_at,
          thumbnail=excluded.thumbnail,
          raw_json=excluded.raw_json
        """,
        (
            video_id,
            v.get("title"),
            v.get("url"),
            v.get("channel") or v.get("channelTitle"),
            v.get("published") or v.get("publishedAt"),
            v.get("thumbnail"),
            v.get("raw_json"),
            now_iso(),
        ),
    )

def insert_bait_hits(conn: sqlite3.Connection, video_id: str, baits: list[dict]) -> int:
    """
    baits: [{bait_key, bait_label, hits, context}]
    """
    if not baits:
        return 0

    inserted = 0
    for b in baits:
        conn.execute(
            """
            INSERT INTO bait_hits (video_id, bait_key, bait_label, hits, context, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                video_id,
                b.get("bait_key") or b.get("key") or "",
                b.get("bait_label") or b.get("label") or "",
                int(b.get("hits") or 1),list
                b.get("context"),
                now_iso(),
            ),
        )
        inserted += 1
    return inserted

def get_baits_for_video(conn: sqlite3.Connection, video_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT bait_key, bait_label, SUM(hits) AS hits
        FROM bait_hits
        WHERE video_id = ?
        GROUP BY bait_key, bait_label
        ORDER BY hits DESC, bait_label ASC
        """,
        (video_id,),
    ).fetchall()
    return [dict(r) for r in rows]

def bait_summary(conn: sqlite3.Connection, days: int = 30) -> list[dict]:
    # simple window by created_at text; ISO sorts lexicographically fine
    rows = conn.execute(
        """
        SELECT bait_key, bait_label, SUM(hits) AS hits, COUNT(DISTINCT video_id) AS videos
        FROM bait_hits
        WHERE created_at >= datetime('now', ?)
        GROUP BY bait_key, bait_label
        ORDER BY hits DESC, bait_label ASC
        """,
        (f"-{int(days)} days",),
    ).fetchall()
    return [dict(r) for r in rows]
