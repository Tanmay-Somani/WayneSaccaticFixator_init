import math
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _angle_to_xy(theta_deg: float, radius: float):
    """Normalized (0..1) coordinates for a point on a spoke at ``theta_deg``
    clockwise from top (12 o'clock) and ``radius`` from the center."""
    theta = math.radians(theta_deg)
    return (
        round(0.5 + radius * math.sin(theta), 4),
        round(0.5 - radius * math.cos(theta), 4),
    )


def build_led_layout(
    spokes: int = 16,
    radii: tuple = (0.18, 0.32, 0.46),
    pattern: tuple = (3, 1),
    center: bool = True,
) -> list:
    """Build the radial fixator layout.

    LEDs sit on ``spokes`` radiating from the center at even angles.
    Consecutive spokes alternate between ``pattern`` counts of lights:
    3 -> 1 -> 3 -> 1 ... On a 3-light spoke the LEDs stack at the inner,
    middle and outer radii. On a 1-light spoke the single LED sits on the
    **outer radius only** — so the full outer ring has 16 LEDs, the middle
    and inner rings have 8 each, plus the center light = 33 total.

    Position 0 is the top (12 o'clock); numbering runs clockwise.
    """
    positions = []
    led_id = 1
    step = 360.0 / spokes
    for i in range(spokes):
        theta = i * step
        count = pattern[i % len(pattern)]
        radii_for_spoke = radii if count > 1 else (radii[-1],)
        for radius in radii_for_spoke:
            x, y = _angle_to_xy(theta, radius)
            positions.append({"id": led_id, "x": x, "y": y, "spoke": i + 1})
            led_id += 1
    if center:
        positions.append({"id": led_id, "x": 0.5, "y": 0.5, "spoke": 0})
    return positions


class Config:
    LED_COUNT = 33
    LED_SPOKES = 16
    LED_RADII = (0.18, 0.32, 0.46)
    LED_SPOKE_PATTERN = (3, 1)
    LED_LAYOUT = build_led_layout(
        spokes=LED_SPOKES,
        radii=LED_RADII,
        pattern=LED_SPOKE_PATTERN,
        center=True,
    )

    INPUT_ID = 1

    RESPONSE_WINDOW_MS = 3000
    WAITING_TIME_MS = 0

    USER_ID = "demo-user"

    DATABASE_PATH = os.path.join(BASE_DIR, "data", "saccadic_fixator.db")
    STATIC_FOLDER = os.path.join(BASE_DIR, "static")

    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    SESSION_TIME_FORMAT = "%Y-%m-%d_%H-%M-%S"

    HOST = "127.0.0.1"
    PORT = 5000
    DEBUG = True
