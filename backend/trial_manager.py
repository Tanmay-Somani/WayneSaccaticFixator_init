import threading
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from backend.database import Database
from backend.input import InputDevice
from backend.led import LED, LEDArray
from backend.models import Trial
from backend.session import SessionManager
from backend.timer import Timer


class TrialManager:
    """Runs the continuous trial loop on a background thread.

    Trial flow (multi-LED fixator):
        pick a random target LED -> turn that LED on -> record LED_ON
        timestamp (monotonic) -> wait -> touch | timeout -> LED off -> save
        -> next trial immediately (random target again).

    Touch handling is coordinate-based: the nearest LED to the tap decides
    the outcome.

    - HIT: the tap maps to the lit target LED -> REACTION_TIME_MS recorded.
    - WRONG TOUCH: the tap maps to a different LED -> ignored (counted in
      ``wrong_touch_count``), the trial keeps waiting for the correct tap.
    - MISS: timeout with no correct tap -> TOUCH_TIMESTAMP = NULL.

    The random target selection (``LEDArray.random_led_id``) is the core
    of the fixator: trials are presented in a random order across the LED
    ring so the user cannot anticipate the next light.
    """

    def __init__(
        self,
        session: SessionManager,
        database: Database,
        led_array: LEDArray,
        input_device: InputDevice,
        response_window_ms: int,
        waiting_time_ms: int = 0,
    ):
        self._session = session
        self._db = database
        self._led_array = led_array
        self._input = input_device
        self.response_window_ms = response_window_ms
        self.waiting_time_ms = waiting_time_ms

        self._touch_event = threading.Event()
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._touch_ts: Optional[int] = None
        self._touch_x: Optional[float] = None
        self._touch_y: Optional[float] = None
        self._trial_active = False
        self._thread: Optional[threading.Thread] = None
        self._last_target_led_id: Optional[int] = None

    # ------------------------------------------------------------------
    # Public control
    # ------------------------------------------------------------------

    def start(self) -> None:
        with self._state_lock:
            old_thread = self._thread

        if old_thread and old_thread.is_alive():
            self._stop_event.set()
            old_thread.join(timeout=2.0)

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, name="trial-manager", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._session.stop()

    def is_running(self) -> bool:
        return self._session.is_running

    def trigger_touch(self, x: float, y: float) -> bool:
        """Called by the input route with a normalized (0..1) coordinate.
        Latch the touch if a trial is active, otherwise ignore it."""
        with self._state_lock:
            if not self._trial_active:
                return False
            self._touch_ts = Timer.now_ns()
            self._touch_x = x
            self._touch_y = y
            self._touch_event.set()
            return True

    def led_is_on(self) -> bool:
        return self._led_array.any_on()

    def active_led_id(self) -> Optional[int]:
        return self._led_array.active_led_id()

    @property
    def led_array(self) -> LEDArray:
        return self._led_array

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        try:
            while self._session.is_running and not self._stop_event.is_set():
                self._run_one_trial()
        finally:
            self._led_array.turn_off()

    def _run_one_trial(self) -> None:
        target_led_id = self._led_array.random_led_id(
            exclude=self._last_target_led_id
        )
        self._last_target_led_id = target_led_id

        with self._state_lock:
            self._touch_event.clear()
            self._touch_ts = None
            self._touch_x = None
            self._touch_y = None
            self._trial_active = False

        self._led_array.turn_off()
        self._led_array.turn_on(target_led_id)
        led_on_ns = Timer.now_ns()
        deadline_ns = led_on_ns + self.response_window_ms * 1_000_000

        with self._state_lock:
            self._trial_active = True

        outcome: Optional[Tuple[str, Optional[int], Optional[int], Optional[float], Optional[float], int]] = None
        wrong_touch_count = 0
        while self._session.is_running and not self._stop_event.is_set():
            if self._touch_event.wait(timeout=0.001):
                with self._state_lock:
                    touch_ts = self._touch_ts
                    touch_x = self._touch_x
                    touch_y = self._touch_y
                    self._touch_event.clear()
                    self._touch_ts = None
                    self._touch_x = None
                    self._touch_y = None

                if touch_ts is None or touch_x is None or touch_y is None:
                    continue

                touched_led_id = self._led_array.nearest_led(touch_x, touch_y)
                if touched_led_id == target_led_id:
                    outcome = (
                        "HIT",
                        touch_ts,
                        touched_led_id,
                        touch_x,
                        touch_y,
                        wrong_touch_count,
                    )
                    break
                wrong_touch_count += 1

            if Timer.now_ns() >= deadline_ns:
                outcome = (
                    "MISS",
                    None,
                    None,
                    None,
                    None,
                    wrong_touch_count,
                )
                break

        self._led_array.turn_off()
        with self._state_lock:
            self._trial_active = False

        if outcome is None:
            return  # session stopped mid-trial; discard the partial trial

        self._finalize_trial(led_on_ns, target_led_id, outcome)

    def _finalize_trial(
        self,
        led_on_ns: int,
        target_led_id: int,
        outcome: Tuple[str, Optional[int], Optional[int], Optional[float], Optional[float], int],
    ) -> None:
        hit_miss, touch_ts, touch_led_id, touch_x, touch_y, wrong_touch_count = outcome
        reaction_time_ms: Optional[float] = None
        if touch_ts is not None:
            reaction_time_ms = Timer.elapsed_ms(led_on_ns, touch_ts)

        trial = Trial(
            trial_id=self._session.next_trial_id(),
            user_id=self._session.user_id,
            system_time=datetime.now(timezone.utc).isoformat(),
            led_id=target_led_id,
            led_on_timestamp=led_on_ns,
            touch_timestamp=touch_ts,
            reaction_time_ms=reaction_time_ms,
            waiting_time_ms=self.waiting_time_ms,
            hit_miss=hit_miss,
            session_id=self._session.session_id,
            touch_led_id=touch_led_id,
            touch_x=touch_x,
            touch_y=touch_y,
            wrong_touch_count=wrong_touch_count,
        )

        self._db.insert_trial(trial)
        self._session.register_trial(trial)
