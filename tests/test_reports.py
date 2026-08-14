import csv
import json
from datetime import datetime, timezone

from backend.reports import exporter
from backend.reports.report import generate_run_report


def _trial(trial_id, hit_miss="HIT", rt=250.0, session_id="2026-08-14_15-30-00"):
    from backend.models import Trial

    return Trial(
        trial_id=trial_id,
        session_id=session_id,
        user_id="alice",
        system_time=datetime.now(timezone.utc).isoformat(),
        led_id=1,
        led_on_timestamp=1_000_000,
        touch_timestamp=1_250_000 if hit_miss == "HIT" else None,
        reaction_time_ms=rt if hit_miss == "HIT" else None,
        waiting_time_ms=0.0,
        hit_miss=hit_miss,
        touch_led_id=1 if hit_miss == "HIT" else None,
        touch_x=0.2 if hit_miss == "HIT" else None,
        touch_y=0.2 if hit_miss == "HIT" else None,
        wrong_touch_count=0 if hit_miss == "HIT" else 1,
    )


def _sample_trials():
    return [
        _trial(1, "HIT", 210.0),
        _trial(2, "HIT", 330.0),
        _trial(3, "MISS"),
        _trial(4, "HIT", 275.0),
    ]


def test_csv_headers_and_rows(tmp_path):
    path = exporter.write_csv(_sample_trials(), tmp_path / "run_data.csv")
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert reader.fieldnames == exporter.CSV_COLUMNS
    assert len(rows) == 4
    assert rows[0]["hit_miss"] == "HIT"
    assert rows[0]["reaction_time_ms"] == "210.0"
    assert rows[0]["touch_led_id"] == "1"
    assert rows[0]["touch_x"] == "0.2"
    assert rows[0]["wrong_touch_count"] == "0"
    assert rows[2]["hit_miss"] == "MISS"
    assert rows[2]["reaction_time_ms"] == ""
    assert rows[2]["touch_timestamp"] == ""
    assert rows[2]["touch_led_id"] == ""
    assert rows[0]["session_id"] == "2026-08-14_15-30-00"


def test_summary_json(tmp_path):
    from backend.reaction_time import ReactionTimeCalculator

    stats = ReactionTimeCalculator.stats(_sample_trials())
    path = exporter.write_summary_json(
        "alice", "2026-08-14_15-30-00", _sample_trials(), stats, tmp_path / "summary.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["user_id"] == "alice"
    assert payload["session_id"] == "2026-08-14_15-30-00"
    assert payload["trial_count"] == 4
    assert payload["stats"]["total_trials"] == 4
    assert payload["stats"]["hits"] == 3
    assert payload["stats"]["misses"] == 1


def test_generate_run_report_writes_all_files(tmp_path):
    report = generate_run_report(
        user_id="alice",
        session_id="2026-08-14_15-30-00",
        trials=_sample_trials(),
        response_window_ms=3000,
        output_dir=tmp_path,
    )

    run_dir = tmp_path / "alice" / "2026-08-14_15-30-00"
    assert (run_dir / "run_data.csv").exists()
    assert (run_dir / "summary.json").exists()

    expected = [
        "reaction_time_series.png",
        "rt_histogram.png",
        "hit_miss_pie.png",
        "cumulative_avg_rt.png",
        "led_accuracy.png",
        "tap_map.png",
    ]
    for name in expected:
        png = run_dir / "graphs" / name
        assert png.exists(), f"{name} missing"
        assert png.stat().st_size > 1000, f"{name} is empty"

    assert report["user_id"] == "alice"
    assert report["session_id"] == "2026-08-14_15-30-00"
    assert report["path"] == str(run_dir)


def test_generate_run_report_with_only_misses(tmp_path):
    trials = [_trial(1, "MISS"), _trial(2, "MISS")]
    report = generate_run_report(
        user_id="bob",
        session_id="2026-08-14_16-00-00",
        trials=trials,
        response_window_ms=3000,
        output_dir=tmp_path,
    )
    run_dir = tmp_path / "bob" / "2026-08-14_16-00-00"
    assert len(list((run_dir / "graphs").glob("*.png"))) == 6
    assert report["session_id"] == "2026-08-14_16-00-00"


def test_generate_run_report_empty_session(tmp_path):
    report = generate_run_report(
        user_id="carol",
        session_id="2026-08-14_17-00-00",
        trials=[],
        response_window_ms=3000,
        output_dir=tmp_path,
    )
    run_dir = tmp_path / "carol" / "2026-08-14_17-00-00"
    assert (run_dir / "run_data.csv").exists()
    assert len(list((run_dir / "graphs").glob("*.png"))) == 6


def test_full_run_report_via_manager(tmp_path, session):
    from helpers import wait_for
    from backend.database import Database
    from backend.input import InputDevice
    from backend.trial_manager import TrialManager
    from conftest import make_led_array

    db = Database(str(tmp_path / "run.db"))
    manager = TrialManager(
        session=session,
        database=db,
        led_array=make_led_array(),
        input_device=InputDevice(1),
        response_window_ms=3000,
    )

    session.start()
    manager.start()
    assert wait_for(manager.led_is_on)
    target = manager.active_led_id()
    x, y = manager.led_array.position_of(target)
    assert wait_for(lambda: manager.trigger_touch(x, y))
    assert wait_for(lambda: session.last_trial() is not None)
    manager.stop()

    report = generate_run_report(
        user_id=session.user_id,
        session_id=session.session_id,
        trials=session.trials(),
        response_window_ms=3000,
        output_dir=tmp_path,
    )

    run_dir = tmp_path / "test-user" / session.session_id
    assert (run_dir / "run_data.csv").exists()
    assert (run_dir / "summary.json").exists()
    assert len(list((run_dir / "graphs").glob("*.png"))) == 6

    with open(run_dir / "run_data.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["hit_miss"] == "HIT"
    assert rows[0]["touch_led_id"] == str(target)
    assert rows[0]["session_id"] == session.session_id
