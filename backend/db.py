# backend/db.py
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = os.getenv("RAYBURN_DB_PATH", os.path.join("data", "rayburn.db"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Safer concurrency for local dev
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """
    Creates tables if they don't exist.
    If you ever see 'sqlite3.DatabaseError: file is not a database',
    delete the bad file at data/rayburn.db and restart.
    """
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS videos (
              video_id TEXT PRIMARY KEY,
              title TEXT,
              channel TEXT,
              published TEXT,
              url TEXT,
              thumbnail TEXT,
              source TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ramps (
              ramp_id TEXT PRIMARY KEY,
              name TEXT,
              lat REAL,
              lng REAL,
              ramp_type TEXT,
              raw_json TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS links (
              link_id TEXT PRIMARY KEY,
              video_id TEXT NOT NULL,
              ramp_id TEXT NOT NULL,
              confidence INTEGER NOT NULL DEFAULT 75,
              created_at TEXT NOT NULL,
              FOREIGN KEY(video_id) REFERENCES videos(video_id) ON DELETE CASCADE,
              FOREIGN KEY(ramp_id) REFERENCES ramps(ramp_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS baits (
              bait_id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE,
              category TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bait_hits (
              hit_id INTEGER PRIMARY KEY AUTOINCREMENT,
              video_id TEXT NOT NULL,
              bait_id INTEGER NOT NULL,
              bait_text TEXT,              -- what matched in transcript (alias/phrase)
              snippet TEXT,                -- small excerpt around the mention
              t_start REAL,                -- seconds
              t_end REAL,                  -- seconds
              confidence INTEGER NOT NULL DEFAULT 70,
              created_at TEXT NOT NULL,
              FOREIGN KEY(video_id) REFERENCES videos(video_id) ON DELETE CASCADE,
              FOREIGN KEY(bait_id) REFERENCES baits(bait_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_bait_hits_video ON bait_hits(video_id);
            CREATE INDEX IF NOT EXISTS idx_bait_hits_bait ON bait_hits(bait_id);
            CREATE INDEX IF NOT EXISTS idx_links_video ON links(video_id);
            CREATE INDEX IF NOT EXISTS idx_links_ramp ON links(ramp_id);
            """
        )


def one(conn: sqlite3.Connection, sql: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def many(conn: sqlite3.Connection, sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    cur = conn.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def upsert_video(conn: sqlite3.Connection, v: Dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO videos(video_id, title, channel, published, url, thumbnail, source, created_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
          title=excluded.title,
          channel=excluded.channel,
          published=excluded.published,
          url=excluded.url,
          thumbnail=excluded.thumbnail,
          source=excluded.source
        """,
        (
            v.get("video_id"),
            v.get("title"),
            v.get("channel"),
            v.get("published"),
            v.get("url"),
            v.get("thumbnail"),
            v.get("source"),
            v.get("created_at", now_iso()),
        ),
    )


def upsert_ramp(conn: sqlite3.Connection, r: Dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO ramps(ramp_id, name, lat, lng, ramp_type, raw_json, created_at)
        VALUES(?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ramp_id) DO UPDATE SET
          name=excluded.name,
          lat=excluded.lat,
          lng=excluded.lng,
          ramp_type=excluded.ramp_type,
          raw_json=excluded.raw_json
        """,
        (
            r.get("ramp_id"),
            r.get("name"),
            r.get("lat"),
            r.get("lng"),
            r.get("ramp_type"),
            r.get("raw_json"),
            r.get("created_at", now_iso()),
        ),
    )


def create_link(conn: sqlite3.Connection, link: Dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO links(link_id, video_id, ramp_id, confidence, created_at)
        VALUES(?, ?, ?, ?, ?)
        """,
        (
            link.get("link_id"),
            link.get("video_id"),
            link.get("ramp_id"),
            int(link.get("confidence", 75)),
            link.get("created_at", now_iso()),
        ),
    )


def ensure_bait(conn: sqlite3.Connection, name: str, category: Optional[str] = None) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("bait name is empty")

    row = one(conn, "SELECT bait_id FROM baits WHERE name = ?", (name,))
    if row:
        return int(row["bait_id"])

    conn.execute(
        "INSERT INTO baits(name, category, created_at) VALUES(?, ?, ?)",
        (name, category, now_iso()),
    )
    row2 = one(conn, "SELECT bait_id FROM baits WHERE name = ?", (name,))
    return int(row2["bait_id"])


def insert_bait_hits(conn: sqlite3.Connection, video_id: str, hits: List[Dict[str, Any]]) -> int:
    """
    hits items expected keys:
      bait_name (required) - canonical
      bait_text (optional) - matched phrase
      snippet (optional)
      t_start (optional) float seconds
      t_end (optional) float seconds
      confidence (optional) int
      category (optional)
    """
    count = 0
    for h in hits:
        bait_name = h.get("bait_name") or h.get("name")
        category = h.get("category")
        bait_id = ensure_bait(conn, bait_name, category=category)

        conn.execute(
            """
            INSERT INTO bait_hits(video_id, bait_id, bait_text, snippet, t_start, t_end, confidence, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                video_id,
                bait_id,
                h.get("bait_text"),
                h.get("snippet"),
                h.get("t_start"),
                h.get("t_end"),
                int(h.get("confidence", 70)),
                now_iso(),
            ),
        )
        count += 1
    return count


def get_baits_for_video(conn: sqlite3.Connection, video_id: str) -> List[Dict[str, Any]]:
    return many(
        conn,
        """
        SELECT
          bh.hit_id,
          v.video_id,
          b.name AS bait_name,
          b.category,
          bh.bait_text,
          bh.snippet,
          bh.t_start,
          bh.t_end,
          bh.confidence,
          bh.created_at
        FROM bait_hits bh
        JOIN baits b ON b.bait_id = bh.bait_id
        JOIN videos v ON v.video_id = bh.video_id
        WHERE v.video_id = ?
        ORDER BY bh.created_at DESC
        """,
        (video_id,),
    )


def bait_summary(conn: sqlite3.Connection, limit: int = 25) -> List[Dict[str, Any]]:
    return many(
        conn,
        """
        SELECT
          b.name AS bait_name,
          b.category,
          COUNT(*) AS hits,
          COUNT(DISTINCT bh.video_id) AS videos
        FROM bait_hits bh
        JOIN baits b ON b.bait_id = bh.bait_id
        GROUP BY b.bait_id
        ORDER BY hits DESC
        LIMIT ?
        """,
        (int(limit),),
    )
