"""SQLite and JSON database for tracking processed tweets and alert history."""
import os
import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "tracker.db"
STATE_JSON_PATH = DATA_DIR / "state.json"

def get_utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class TrackerDB:
    def __init__(self, db_path: Optional[Path] = None, state_json_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.state_json_path = state_json_path or STATE_JSON_PATH
        self._ensure_dirs()
        self.init_db()

    def _ensure_dirs(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_json_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize SQLite database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_tweets (
                    id TEXT PRIMARY KEY,
                    handle TEXT NOT NULL,
                    text TEXT,
                    posted_at TEXT,
                    url TEXT,
                    is_newsworthy INTEGER NOT NULL DEFAULT 0,
                    confidence_score INTEGER NOT NULL DEFAULT 0,
                    headline TEXT,
                    summary TEXT,
                    category TEXT,
                    reasoning TEXT,
                    emailed_at TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_handle ON processed_tweets(handle);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_is_newsworthy ON processed_tweets(is_newsworthy);
            """)
            conn.commit()
            
        # If state.json exists but db is empty, import state.json
        if self.state_json_path.exists():
            self._sync_from_state_json()

    def is_tweet_seen(self, tweet_id: str) -> bool:
        """Check if a tweet ID has already been evaluated or stored."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_tweets WHERE id = ?", (str(tweet_id),))
            return cursor.fetchone() is not None

    def save_evaluation(
        self,
        tweet_id: str,
        handle: str,
        text: str,
        posted_at: Optional[str],
        url: str,
        is_newsworthy: bool,
        confidence_score: int,
        headline: str,
        summary: str,
        category: str,
        reasoning: str,
        emailed_at: Optional[str] = None
    ):
        """Save an evaluated tweet to the database."""
        now_str = get_utc_now_iso()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO processed_tweets (
                    id, handle, text, posted_at, url,
                    is_newsworthy, confidence_score, headline,
                    summary, category, reasoning, emailed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(tweet_id),
                handle.lower(),
                text,
                posted_at,
                url,
                1 if is_newsworthy else 0,
                confidence_score,
                headline,
                summary,
                category,
                reasoning,
                emailed_at,
                now_str
            ))
            conn.commit()
            
        self.export_state_json()

    def mark_as_emailed(self, tweet_id: str):
        """Update emailed_at timestamp for an alert."""
        now_str = get_utc_now_iso()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE processed_tweets SET emailed_at = ? WHERE id = ?
            """, (now_str, str(tweet_id)))
            conn.commit()
        self.export_state_json()

    def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent newsworthy alerts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM processed_tweets
                WHERE is_newsworthy = 1
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def export_state_json(self, path: Optional[Path] = None):
        """Export seen tweet IDs to a portable JSON file for git commits/sync."""
        export_path = path or self.state_json_path
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, handle, is_newsworthy, confidence_score, emailed_at, created_at
                FROM processed_tweets
                ORDER BY created_at DESC LIMIT 5000
            """)
            rows = [dict(row) for row in cursor.fetchall()]
        
        state_data = {
            "last_updated": get_utc_now_iso(),
            "total_seen": len(rows),
            "tweets": rows
        }
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

    def _sync_from_state_json(self):
        """Sync seen IDs from state.json if SQLite is empty (e.g. fresh runner in CI)."""
        try:
            with open(self.state_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tweets = data.get("tweets", [])
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM processed_tweets")
                if cursor.fetchone()[0] == 0 and tweets:
                    for t in tweets:
                        cursor.execute("""
                            INSERT OR IGNORE INTO processed_tweets (
                                id, handle, is_newsworthy, confidence_score, emailed_at, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            str(t.get("id")),
                            t.get("handle", ""),
                            t.get("is_newsworthy", 0),
                            t.get("confidence_score", 0),
                            t.get("emailed_at"),
                            t.get("created_at", get_utc_now_iso())
                        ))
                    conn.commit()
        except Exception:
            pass
