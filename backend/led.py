import random
import threading
from typing import List, Optional


class LED:
    """A single LED light with a normalized (0..1) position on the board.

    For this MVP the LED is software-emulated: the state lives in memory.
    A future hardware driver can subclass this and keep the same public
    interface without changing trial logic.
    """

    def __init__(self, led_id: int, x: float = 0.5, y: float = 0.5):
        self.led_id = led_id
        self.x = x
        self.y = y
        self._state = False
        self._lock = threading.Lock()

    def turn_on(self) -> None:
        with self._lock:
            self._state = True

    def turn_off(self) -> None:
        with self._lock:
            self._state = False

    def is_on(self) -> bool:
        with self._lock:
            return self._state


class LEDArray:
    """The full LED board. Exactly one light can be lit at a time.

    Manages the on/off state across all LEDs, picks the random target for
    each trial, and maps a touch coordinate (normalized x, y) to the nearest
    LED on the board.
    """

    def __init__(self, lights: List[LED]):
        self._lights = list(lights)
        self._active_led_id: Optional[int] = None
        self._lock = threading.Lock()

    @property
    def lights(self) -> List[LED]:
        return list(self._lights)

    def led_ids(self) -> List[int]:
        return [led.led_id for led in self._lights]

    def positions(self) -> List[dict]:
        return [
            {"id": led.led_id, "x": led.x, "y": led.y} for led in self._lights
        ]

    def position_of(self, led_id: int) -> Optional[tuple]:
        for led in self._lights:
            if led.led_id == led_id:
                return (led.x, led.y)
        return None

    def random_led_id(self, exclude: Optional[int] = None) -> int:
        """Pick the next random target LED — the core randomization of the
        fixator. Uniform over the lights, with an optional ``exclude`` so the
        LED that was just tapped is not immediately re-lit. The exclusion
        lasts a single pick only: as soon as another LED becomes the target,
        the excluded one is back in the pool."""
        candidates = [
            led.led_id for led in self._lights if led.led_id != exclude
        ]
        if not candidates:
            candidates = self.led_ids()
        return random.choice(candidates)

    def turn_on(self, led_id: int) -> None:
        with self._lock:
            for led in self._lights:
                if led.led_id == led_id:
                    led.turn_on()
                    self._active_led_id = led_id
                else:
                    led.turn_off()

    def turn_off(self) -> None:
        with self._lock:
            for led in self._lights:
                led.turn_off()
            self._active_led_id = None

    def active_led_id(self) -> Optional[int]:
        with self._lock:
            return self._active_led_id

    def any_on(self) -> bool:
        return self.active_led_id() is not None

    def nearest_led(self, x: float, y: float) -> int:
        """Map a normalized touch coordinate to the nearest LED id using
        squared Euclidean distance. Ties resolve to the lowest id."""
        best_id = None
        best_distance = None
        for led in self._lights:
            distance = (led.x - x) ** 2 + (led.y - y) ** 2
            if best_distance is None or distance < best_distance:
                best_id = led.led_id
                best_distance = distance
        return best_id
