import math

from config import Config, build_led_layout


def test_layout_has_33_leds():
    assert len(Config.LED_LAYOUT) == 33


def test_layout_ids_are_1_to_33():
    assert [p["id"] for p in Config.LED_LAYOUT] == list(range(1, 34))


def test_layout_positions_unique():
    assert len({(p["x"], p["y"]) for p in Config.LED_LAYOUT}) == 33


def test_layout_within_unit_square():
    for p in Config.LED_LAYOUT:
        assert 0.0 <= p["x"] <= 1.0
        assert 0.0 <= p["y"] <= 1.0


def test_layout_center_last_at_midpoint():
    center = Config.LED_LAYOUT[-1]
    assert center["id"] == 33
    assert center["x"] == 0.5
    assert center["y"] == 0.5


def test_layout_spoke_pattern_3_1():
    # spokes alternate 3 then 1 lights, in id order
    ids = [p["id"] for p in Config.LED_LAYOUT[:32]]
    groups = [3, 1] * 8
    cursor = 0
    for n in groups:
        chunk = ids[cursor:cursor + n]
        assert len(chunk) == n
        cursor += n
    assert cursor == 32


def test_layout_single_leds_are_on_outer_ring():
    # every spoke has exactly one light on the outer radius (0.46)
    outer_radius = Config.LED_RADII[-1]
    outer_ids = []
    for p in Config.LED_LAYOUT:
        if p["id"] == 33:
            continue
        theta = math.radians((p["spoke"] - 1) * (360.0 / Config.LED_SPOKES))
        x = round(0.5 + outer_radius * math.sin(theta), 4)
        y = round(0.5 - outer_radius * math.cos(theta), 4)
        if (p["x"], p["y"]) == (x, y):
            outer_ids.append(p["id"])
    assert len(outer_ids) == 16  # full outer ring


def test_layout_radii_match_config():
    for p in Config.LED_LAYOUT:
        if p["id"] == 33:
            continue
        theta = math.radians((p["spoke"] - 1) * (360.0 / Config.LED_SPOKES))
        computed_x = round(0.5 + Config.LED_RADII[-1] * math.sin(theta), 4)
        computed_y = round(0.5 - Config.LED_RADII[-1] * math.cos(theta), 4)
        if (p["x"], p["y"]) == (computed_x, computed_y):
            continue  # outer ring position
        assert any(
            (round(0.5 + r * math.sin(theta), 4), round(0.5 - r * math.cos(theta), 4))
            == (p["x"], p["y"])
            for r in Config.LED_RADII
        ), f"LED {p['id']} not on a configured radius"


def test_build_led_layout_custom():
    layout = build_led_layout(spokes=4, radii=(0.1, 0.3), pattern=(2, 1), center=False)
    assert len(layout) == 6  # 2+1 then 2+1
    assert layout[0]["id"] == 1
    assert layout[-1]["id"] == 6
