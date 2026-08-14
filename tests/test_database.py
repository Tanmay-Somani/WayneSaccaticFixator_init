from datetime import datetime, timezone

from backend.database import Database
from backend.models import Trial


def _make_trial(trial_id=1, hit_miss="HIT", rt=None, touch_ts=None):
    return Trial(
        trial_id=trial_id,
        user_id="test-user",
        system_time=datetime.now(timezone.utc).isoformat(),
        led_id=1,
        led_on_timestamp=1_000_000,
        touch_timestamp=touch_ts,
        reaction_time_ms=rt,
        waiting_time_ms=0.0,
        hit_miss=hit_miss,
    )


def test_insert_and_fetch_round_trip(db):
    trial = _make_trial(rt=250.5, touch_ts=1_250_500_000)
    trial.touch_led_id = 1
    trial.touch_x = 0.2
    trial.touch_y = 0.2
    trial.wrong_touch_count = 1
    db.insert_trial(trial)

    rows = db.fetch_trials(user_id="test-user")
    assert len(rows) == 1
    stored = rows[0]
    assert stored.trial_id == 1
    assert stored.user_id == "test-user"
    assert stored.led_id == 1
    assert stored.led_on_timestamp == 1_000_000
    assert stored.touch_timestamp == 1_250_500_000
    assert stored.reaction_time_ms == 250.5
    assert stored.waiting_time_ms == 0.0
    assert stored.hit_miss == "HIT"
    assert stored.touch_led_id == 1
    assert stored.touch_x == 0.2
    assert stored.touch_y == 0.2
    assert stored.wrong_touch_count == 1


def test_insert_miss_stores_nulls(db):
    trial = _make_trial(hit_miss="MISS", rt=None, touch_ts=None)
    db.insert_trial(trial)

    rows = db.fetch_trials(user_id="test-user")
    assert len(rows) == 1
    stored = rows[0]
    assert stored.hit_miss == "MISS"
    assert stored.touch_timestamp is None
    assert stored.reaction_time_ms is None


def test_fetch_filters_by_user(db):
    db.insert_trial(_make_trial())
    db.insert_trial(Trial(
        trial_id=1,
        user_id="other-user",
        system_time=datetime.now(timezone.utc).isoformat(),
        led_id=1,
        led_on_timestamp=2_000_000,
        touch_timestamp=None,
        reaction_time_ms=None,
        waiting_time_ms=0.0,
        hit_miss="MISS",
    ))

    rows = db.fetch_trials(user_id="test-user")
    assert len(rows) == 1
    assert rows[0].user_id == "test-user"


def test_waiting_time_column_exists(db):
    columns = db._connect().execute("PRAGMA table_info(trials)").fetchall()
    names = [row["name"] for row in columns]
    assert "waiting_time_ms" in names
    assert "led_on_timestamp" in names
    assert "session_id" in names
    assert "touch_led_id" in names
    assert "touch_x" in names
    assert "touch_y" in names
    assert "wrong_touch_count" in names


def test_session_id_round_trip(db):
    trial = _make_trial()
    trial.session_id = "2026-08-14_15-30-00"
    db.insert_trial(trial)

    rows = db.fetch_trials(user_id="test-user")
    assert rows[0].session_id == "2026-08-14_15-30-00"


def test_migration_adds_session_id_to_existing_db(tmp_path):
    import sqlite3

    db_path = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE trials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trial_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            system_time TEXT NOT NULL,
            led_id INTEGER NOT NULL,
            led_on_timestamp INTEGER NOT NULL,
            touch_timestamp INTEGER,
            reaction_time_ms REAL,
            waiting_time_ms REAL NOT NULL DEFAULT 0,
            hit_miss TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

    upgraded = Database(db_path)
    columns = upgraded._connect().execute("PRAGMA table_info(trials)").fetchall()
    names = [row["name"] for row in columns]
    assert "session_id" in names
    assert "touch_led_id" in names
    assert "touch_x" in names
    assert "touch_y" in names
    assert "wrong_touch_count" in names
