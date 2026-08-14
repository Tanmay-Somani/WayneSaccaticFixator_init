from backend.led import LED, LEDArray
from conftest import TEST_LED_POSITIONS


def _array():
    return LEDArray(
        [LED(p["id"], x=p["x"], y=p["y"]) for p in TEST_LED_POSITIONS]
    )


def test_positions_match_layout():
    arr = _array()
    assert arr.positions() == TEST_LED_POSITIONS


def test_exactly_one_light_active():
    arr = _array()
    arr.turn_on(2)
    assert arr.active_led_id() == 2
    assert arr.any_on()
    for led in arr.lights:
        assert led.is_on() == (led.led_id == 2)

    arr.turn_on(4)
    assert arr.active_led_id() == 4
    for led in arr.lights:
        assert led.is_on() == (led.led_id == 4)

    arr.turn_off()
    assert arr.active_led_id() is None
    assert not arr.any_on()


def test_random_led_id_within_board():
    arr = _array()
    ids = {arr.random_led_id() for _ in range(200)}
    assert ids == set(arr.led_ids())


def test_random_led_id_excludes_for_one_pick():
    arr = _array()
    picks = [arr.random_led_id(exclude=3) for _ in range(300)]
    assert 3 not in picks
    assert set(picks) == {1, 2, 4, 5}

    picks = [arr.random_led_id(exclude=5) for _ in range(300)]
    assert 5 not in picks
    assert set(picks) == {1, 2, 3, 4}


def test_random_led_id_exclude_falls_back_to_full_set():
    arr = LEDArray([LED(1)])
    picks = [arr.random_led_id(exclude=1) for _ in range(50)]
    assert set(picks) == {1}


def test_nearest_led_mapping():
    arr = _array()
    assert arr.nearest_led(0.2, 0.2) == 1
    assert arr.nearest_led(0.8, 0.2) == 2
    assert arr.nearest_led(0.8, 0.8) == 3
    assert arr.nearest_led(0.2, 0.8) == 4
    assert arr.nearest_led(0.5, 0.5) == 5
    assert arr.nearest_led(0.25, 0.25) == 1
    assert arr.nearest_led(0.6, 0.6) == 5
    assert arr.nearest_led(0.0, 0.0) == 1
    assert arr.nearest_led(1.0, 1.0) == 3
