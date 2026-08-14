from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class User:
    user_id: str
    name: str = ""


@dataclass
class Trial:
    trial_id: int
    user_id: str
    system_time: str
    led_id: int
    led_on_timestamp: int
    touch_timestamp: Optional[int]
    reaction_time_ms: Optional[float]
    waiting_time_ms: float
    hit_miss: str
    session_id: str = ""
    touch_led_id: Optional[int] = None
    touch_x: Optional[float] = None
    touch_y: Optional[float] = None
    wrong_touch_count: int = 0

    @property
    def is_hit(self) -> bool:
        return self.hit_miss == "HIT"

    @property
    def is_wrong_touch(self) -> bool:
        return self.wrong_touch_count > 0


@dataclass
class SessionStats:
    total_trials: int = 0
    hits: int = 0
    misses: int = 0
    hit_percentage: float = 0.0
    avg_rt_ms: Optional[float] = None
    median_rt_ms: Optional[float] = None
    min_rt_ms: Optional[float] = None
    max_rt_ms: Optional[float] = None
    stddev_rt_ms: Optional[float] = None
    per_led: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_trials": self.total_trials,
            "hits": self.hits,
            "misses": self.misses,
            "hit_percentage": round(self.hit_percentage, 1),
            "avg_rt_ms": self._round(self.avg_rt_ms),
            "median_rt_ms": self._round(self.median_rt_ms),
            "min_rt_ms": self._round(self.min_rt_ms),
            "max_rt_ms": self._round(self.max_rt_ms),
            "stddev_rt_ms": self._round(self.stddev_rt_ms),
            "per_led": {
                str(led_id): stats.to_dict()
                for led_id, stats in self.per_led.items()
            },
        }

    @staticmethod
    def _round(value: Optional[float]):
        return None if value is None else round(value, 1)
