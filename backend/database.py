import os
import sqlite3
from typing import List, Optional

from backend.models import Trial


class Database:
    """SQLite persistence for trials. Uses a short-lived connection per
    operation so it is safe to call from multiple threads."""

    def __init__(self, path: str):
        self.path = path
        self._ensure_dir()
        self._init_schema()

    def _ensure_dir(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trial_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    system_time TEXT NOT NULL,
                    led_id INTEGER NOT NULL,
                    led_on_timestamp INTEGER NOT NULL,
                    touch_timestamp INTEGER,
                    reaction_time_ms REAL,
                    waiting_time_ms REAL NOT NULL DEFAULT 0,
                    hit_miss TEXT NOT NULL,
                    session_id TEXT NOT NULL DEFAULT '',
                    touch_led_id INTEGER,
                    touch_x REAL,
                    touch_y REAL,
                    wrong_touch_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_trials_user ON trials(user_id)"
            )
            self._migrate(conn)
            conn.commit()

    def _migrate(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(trials)")}
        additions = {
            "session_id": "TEXT NOT NULL DEFAULT ''",
            "touch_led_id": "INTEGER",
            "touch_x": "REAL",
            "touch_y": "REAL",
            "wrong_touch_count": "INTEGER NOT NULL DEFAULT 0",
        }
        for column, definition in additions.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE trials ADD COLUMN {column} {definition}")

    def insert_trial(self, trial: Trial) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO trials (
                    trial_id, user_id, system_time, led_id,
                    led_on_timestamp, touch_timestamp,
                    reaction_time_ms, waiting_time_ms, hit_miss, session_id,
                    touch_led_id, touch_x, touch_y, wrong_touch_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trial.trial_id,
                    trial.user_id,
                    trial.system_time,
                    trial.led_id,
                    trial.led_on_timestamp,
                    trial.touch_timestamp,
                    trial.reaction_time_ms,
                    trial.waiting_time_ms,
                    trial.hit_miss,
                    trial.session_id,
                    trial.touch_led_id,
                    trial.touch_x,
                    trial.touch_y,
                    trial.wrong_touch_count,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def fetch_trials(self, user_id: Optional[str] = None, limit: int = 100) -> List[Trial]:
        query = "SELECT * FROM trials"
        params: List[str] = []
        if user_id:
            query += " WHERE user_id = ?"
            params.append(user_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_trial(row) for row in rows]

    @staticmethod
    def _row_to_trial(row: sqlite3.Row) -> Trial:
        return Trial(
            trial_id=row["trial_id"],
            user_id=row["user_id"],
            system_time=row["system_time"],
            led_id=row["led_id"],
            led_on_timestamp=row["led_on_timestamp"],
            touch_timestamp=row["touch_timestamp"],
            reaction_time_ms=row["reaction_time_ms"],
            waiting_time_ms=row["waiting_time_ms"],
            hit_miss=row["hit_miss"],
            session_id=row["session_id"],
            touch_led_id=row["touch_led_id"],
            touch_x=row["touch_x"],
            touch_y=row["touch_y"],
            wrong_touch_count=row["wrong_touch_count"],
        )
