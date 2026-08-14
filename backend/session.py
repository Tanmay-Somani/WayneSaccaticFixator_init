import threading
from datetime import datetime
from typing import List, Optional

from backend.models import SessionStats, Trial
from backend.reaction_time import ReactionTimeCalculator


class SessionManager:
    """Tracks the active session: user, running state, trial counter,
    and session statistics."""

    def __init__(self, user_id: str, session_time_format: str = "%Y-%m-%d_%H-%M-%S"):
        self._lock = threading.Lock()
        self.user_id = user_id
        self.session_time_format = session_time_format
        self.running = False
        self.session_id = ""
        self.trial_counter = 0
        self._trials: List[Trial] = []
        self._last_trial: Optional[Trial] = None

    def start(self) -> None:
        with self._lock:
            self.running = True
            self.session_id = datetime.now().strftime(self.session_time_format)
            self.trial_counter = 0
            self._trials = []
            self._last_trial = None

    def stop(self) -> None:
        with self._lock:
            self.running = False

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self.running

    def next_trial_id(self) -> int:
        with self._lock:
            self.trial_counter += 1
            return self.trial_counter

    def register_trial(self, trial: Trial) -> None:
        with self._lock:
            self._trials.append(trial)
            self._last_trial = trial

    def last_trial(self) -> Optional[Trial]:
        with self._lock:
            return self._last_trial

    def trials(self) -> List[Trial]:
        with self._lock:
            return list(self._trials)

    def stats(self, led_ids: Optional[List[int]] = None) -> SessionStats:
        with self._lock:
            trials = list(self._trials)
        return ReactionTimeCalculator.stats(trials, led_ids=led_ids)
