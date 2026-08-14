import threading
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory

from backend.database import Database
from backend.input import InputDevice
from backend.led import LED, LEDArray
from backend.reports.report import generate_run_report
from backend.session import SessionManager
from backend.trial_manager import TrialManager
from config import Config

app = Flask(__name__, static_folder=Config.STATIC_FOLDER)

_session: Optional[SessionManager] = None
_manager: Optional[TrialManager] = None
_database: Optional[Database] = None
_startup_lock = threading.Lock()


def _get_database() -> Database:
    global _database
    if _database is None:
        _database = Database(Config.DATABASE_PATH)
    return _database


def _led_array() -> LEDArray:
    return LEDArray(
        [
            LED(light["id"], x=light["x"], y=light["y"])
            for light in Config.LED_LAYOUT
        ]
    )


def _get_manager() -> TrialManager:
    global _manager, _session
    if _manager is None:
        _session = SessionManager(Config.USER_ID)
        _manager = TrialManager(
            session=_session,
            database=_get_database(),
            led_array=_led_array(),
            input_device=InputDevice(Config.INPUT_ID),
            response_window_ms=Config.RESPONSE_WINDOW_MS,
            waiting_time_ms=Config.WAITING_TIME_MS,
        )
    return _manager


def _state_dict() -> dict:
    manager = _get_manager()
    session = _session
    led_ids = [light["id"] for light in Config.LED_LAYOUT]
    stats = session.stats(led_ids=led_ids)
    last = session.last_trial()

    return {
        "running": session.is_running,
        "led_on": manager.led_is_on(),
        "led_positions": Config.LED_LAYOUT,
        "active_led_id": manager.active_led_id(),
        "input_id": Config.INPUT_ID,
        "response_window_ms": Config.RESPONSE_WINDOW_MS,
        "current_trial": session.trial_counter + 1 if session.is_running else session.trial_counter,
        "last_rt_ms": None if last is None else last.reaction_time_ms,
        "last_hit_miss": None if last is None else last.hit_miss,
        "stats": stats.to_dict(),
    }


@app.route("/")
def index():
    return send_from_directory(Config.STATIC_FOLDER, "index.html")


@app.route("/api/session/start", methods=["POST"])
def start_session():
    manager = _get_manager()
    if not manager.is_running():
        _session.start()
        manager.start()
    return jsonify({"ok": True, "state": _state_dict()})


@app.route("/api/session/stop", methods=["POST"])
def stop_session():
    manager = _get_manager()
    manager.stop()

    report = None
    try:
        report = generate_run_report(
            user_id=_session.user_id,
            session_id=_session.session_id,
            trials=_session.trials(),
            response_window_ms=Config.RESPONSE_WINDOW_MS,
            output_dir=Config.OUTPUT_DIR,
            led_positions=Config.LED_LAYOUT,
        )
    except Exception:
        report = None

    return jsonify({"ok": True, "state": _state_dict(), "report": report})


@app.route("/api/touch", methods=["POST"])
def touch():
    manager = _get_manager()
    body = request.get_json(silent=True) or {}
    input_id = body.get("input_id", Config.INPUT_ID)
    if input_id != Config.INPUT_ID:
        return jsonify({"ok": False, "error": "unknown input_id"}), 400

    x = body.get("x")
    y = body.get("y")
    if x is None or y is None:
        return jsonify({"ok": False, "error": "missing x/y coordinates"}), 400
    try:
        x = float(x)
        y = float(y)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "x/y must be numbers"}), 400
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        return jsonify({"ok": False, "error": "x/y must be within 0..1"}), 400

    accepted = manager.trigger_touch(x, y)
    return jsonify({"ok": accepted})


@app.route("/api/state", methods=["GET"])
def state():
    return jsonify(_state_dict())


@app.route("/api/stats", methods=["GET"])
def stats():
    _get_manager()
    led_ids = [light["id"] for light in Config.LED_LAYOUT]
    return jsonify(_session.stats(led_ids=led_ids).to_dict())


@app.route("/api/trials", methods=["GET"])
def trials():
    user_id = request.args.get("user_id")
    limit = request.args.get("limit", 50, type=int)
    records = _get_database().fetch_trials(user_id=user_id, limit=limit)
    return jsonify([_trial_to_dict(t) for t in records])


def _trial_to_dict(trial) -> dict:
    return {
        "trial_id": trial.trial_id,
        "session_id": trial.session_id,
        "user_id": trial.user_id,
        "system_time": trial.system_time,
        "led_id": trial.led_id,
        "led_on_timestamp": trial.led_on_timestamp,
        "touch_timestamp": trial.touch_timestamp,
        "reaction_time_ms": trial.reaction_time_ms,
        "waiting_time_ms": trial.waiting_time_ms,
        "hit_miss": trial.hit_miss,
        "touch_led_id": trial.touch_led_id,
        "touch_x": trial.touch_x,
        "touch_y": trial.touch_y,
        "wrong_touch_count": trial.wrong_touch_count,
    }


def run():
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)


if __name__ == "__main__":
    run()
