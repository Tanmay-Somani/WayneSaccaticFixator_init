import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from backend.models import SessionStats, Trial

CSV_COLUMNS = [
    "trial_id",
    "session_id",
    "user_id",
    "system_time",
    "led_id",
    "led_on_timestamp",
    "touch_timestamp",
    "reaction_time_ms",
    "waiting_time_ms",
    "hit_miss",
    "touch_led_id",
    "touch_x",
    "touch_y",
    "wrong_touch_count",
]


def write_csv(trials: List[Trial], path: Path) -> Path:
    path = Path(path)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for trial in trials:
            writer.writerow(
                {
                    "trial_id": trial.trial_id,
                    "session_id": trial.session_id,
                    "user_id": trial.user_id,
                    "system_time": trial.system_time,
                    "led_id": trial.led_id,
                    "led_on_timestamp": trial.led_on_timestamp,
                    "touch_timestamp": "" if trial.touch_timestamp is None else trial.touch_timestamp,
                    "reaction_time_ms": "" if trial.reaction_time_ms is None else trial.reaction_time_ms,
                    "waiting_time_ms": trial.waiting_time_ms,
                    "hit_miss": trial.hit_miss,
                    "touch_led_id": "" if trial.touch_led_id is None else trial.touch_led_id,
                    "touch_x": "" if trial.touch_x is None else trial.touch_x,
                    "touch_y": "" if trial.touch_y is None else trial.touch_y,
                    "wrong_touch_count": trial.wrong_touch_count,
                }
            )
    return path


def write_summary_json(
    user_id: str,
    session_id: str,
    trials: List[Trial],
    stats: SessionStats,
    path: Path,
) -> Path:
    path = Path(path)
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trial_count": len(trials),
        "stats": stats.to_dict(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path
