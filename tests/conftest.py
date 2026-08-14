import pytest

from backend.database import Database
from backend.input import InputDevice
from backend.led import LED, LEDArray
from backend.session import SessionManager
from backend.trial_manager import TrialManager


TEST_LED_POSITIONS = [
    {"id": 1, "x": 0.2, "y": 0.2},
    {"id": 2, "x": 0.8, "y": 0.2},
    {"id": 3, "x": 0.8, "y": 0.8},
    {"id": 4, "x": 0.2, "y": 0.8},
    {"id": 5, "x": 0.5, "y": 0.5},
]


def make_led_array():
    return LEDArray(
        [LED(light["id"], x=light["x"], y=light["y"]) for light in TEST_LED_POSITIONS]
    )


@pytest.fixture
def db(tmp_path):
    return Database(str(tmp_path / "test.db"))


@pytest.fixture
def session():
    return SessionManager("test-user")


@pytest.fixture
def led_array():
    return make_led_array()


@pytest.fixture
def manager(db, session, led_array, response_window_ms=3000):
    return TrialManager(
        session=session,
        database=db,
        led_array=led_array,
        input_device=InputDevice(1),
        response_window_ms=response_window_ms,
    )
