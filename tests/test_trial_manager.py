from backend.database import Database
from backend.input import InputDevice
from backend.trial_manager import TrialManager

from conftest import make_led_array
from helpers import wait_for


def _make_manager(db, session, window_ms):
    return TrialManager(
        session=session,
        database=db,
        led_array=make_led_array(),
        input_device=InputDevice(1),
        response_window_ms=window_ms,
    )


def _touch_target(manager):
    target = manager.active_led_id()
    assert target is not None, "no active LED"
    x, y = manager.led_array.position_of(target)
    return target, x, y


def _touch_wrong(manager, target):
    for led_id in manager.led_array.led_ids():
        if led_id != target:
            x, y = manager.led_array.position_of(led_id)
            return x, y
    raise AssertionError("no other LED available")


def test_touch_ignored_when_not_running(manager):
    assert manager.trigger_touch(0.5, 0.5) is False
    assert manager.led_is_on() is False


def test_hit_records_reaction_time(db, session):
    manager = _make_manager(db, session, window_ms=2000)
    session.start()
    manager.start()

    assert wait_for(manager.led_is_on), "LED never turned on"
    target, x, y = _touch_target(manager)
    assert wait_for(lambda: manager.trigger_touch(x, y)), "touch not accepted"

    assert wait_for(lambda: session.last_trial() is not None), "trial never saved"

    last = session.last_trial()
    assert last is not None
    assert last.hit_miss == "HIT"
    assert last.reaction_time_ms is not None
    assert last.reaction_time_ms > 0
    assert last.touch_timestamp is not None
    assert last.led_on_timestamp < last.touch_timestamp
    assert last.led_id == target
    assert last.touch_led_id == target
    assert last.wrong_touch_count == 0
    assert last.waiting_time_ms == 0.0

    assert len(db.fetch_trials()) == 1

    assert wait_for(manager.led_is_on), "next trial did not start"
    _, x2, y2 = _touch_target(manager)
    assert wait_for(lambda: manager.trigger_touch(x2, y2)), "second touch not accepted"
    assert wait_for(
        lambda: session.last_trial() is not None and session.last_trial().trial_id == 2,
        timeout=3.0,
    ), "second trial never saved"
    session.stop()
    assert session.trial_counter == 2
    assert len(db.fetch_trials()) == 2


def test_wrong_touch_then_correct_hit(db, session):
    manager = _make_manager(db, session, window_ms=2000)
    session.start()
    manager.start()

    assert wait_for(manager.led_is_on), "LED never turned on"
    target, _, _ = _touch_target(manager)
    wx, wy = _touch_wrong(manager, target)
    assert manager.trigger_touch(wx, wy), "wrong touch not accepted"
    assert not wait_for(lambda: session.last_trial() is not None, timeout=0.3), "wrong touch ended trial"

    _, x, y = _touch_target(manager)
    assert wait_for(lambda: manager.trigger_touch(x, y)), "correct touch not accepted"
    assert wait_for(lambda: session.last_trial() is not None), "trial never saved"

    last = session.last_trial()
    assert last.hit_miss == "HIT"
    assert last.led_id == target
    assert last.touch_led_id == target
    assert last.wrong_touch_count == 1
    assert last.touch_x == x
    assert last.touch_y == y
    session.stop()


def test_timeout_produces_miss(db, session):
    manager = _make_manager(db, session, window_ms=80)
    session.start()
    manager.start()

    assert wait_for(manager.led_is_on), "LED never turned on"
    assert wait_for(lambda: session.last_trial() is not None, timeout=3.0), "trial never saved"
    session.stop()

    last = session.last_trial()
    assert last.hit_miss == "MISS"
    assert last.touch_timestamp is None
    assert last.reaction_time_ms is None
    assert last.touch_led_id is None
    assert last.touch_x is None
    assert last.touch_y is None
    assert last.waiting_time_ms == 0.0


def test_wrong_touches_only_time_out_as_miss(db, session):
    manager = _make_manager(db, session, window_ms=150)
    session.start()
    manager.start()

    assert wait_for(manager.led_is_on), "LED never turned on"
    target, _, _ = _touch_target(manager)
    wx, wy = _touch_wrong(manager, target)
    assert manager.trigger_touch(wx, wy)
    assert manager.trigger_touch(wx, wy)
    assert wait_for(lambda: session.last_trial() is not None, timeout=3.0), "trial never saved"

    last = session.last_trial()
    assert last.hit_miss == "MISS"
    assert last.wrong_touch_count >= 1
    assert last.touch_led_id is None
    session.stop()


def test_next_trial_starts_immediately(db, session):
    manager = _make_manager(db, session, window_ms=80)
    session.start()
    manager.start()

    assert wait_for(lambda: len(db.fetch_trials()) >= 3, timeout=3.0), "no repeated trials"
    session.stop()

    assert session.trial_counter == 3
    assert len(db.fetch_trials()) == 3
    for trial in db.fetch_trials():
        assert trial.hit_miss == "MISS"


def test_random_targets_spread_across_leds(db, session):
    manager = _make_manager(db, session, window_ms=40)
    session.start()
    manager.start()

    assert wait_for(lambda: len(db.fetch_trials()) >= 60, timeout=8.0), "not enough trials"
    session.stop()

    used = {trial.led_id for trial in db.fetch_trials()}
    assert used <= set(manager.led_array.led_ids())
    assert len(used) >= 3, f"random target selection too narrow: {used}"


def test_consecutive_targets_never_repeat(db, session):
    manager = _make_manager(db, session, window_ms=40)
    session.start()
    manager.start()

    assert wait_for(lambda: len(db.fetch_trials()) >= 40, timeout=8.0), "not enough trials"
    session.stop()

    trials = db.fetch_trials()
    ids = [trial.led_id for trial in trials]
    for a, b in zip(ids, ids[1:]):
        assert a != b, f"LED {a} repeated back-to-back"


def test_stop_mid_trial_discards_partial(db, session):
    manager = _make_manager(db, session, window_ms=3000)
    session.start()
    manager.start()

    assert wait_for(manager.led_is_on), "LED never turned on"
    manager.stop()
    assert wait_for(lambda: session.trial_counter == 0), "partial trial was saved"

    assert len(db.fetch_trials()) == 0


def test_restart_after_stop(db, session):
    manager = _make_manager(db, session, window_ms=300)
    session.start()
    manager.start()

    assert wait_for(manager.led_is_on), "LED never turned on"
    target, x, y = _touch_target(manager)
    assert wait_for(lambda: manager.trigger_touch(x, y))
    assert wait_for(lambda: session.last_trial() is not None, timeout=3.0), "trial never saved"
    manager.stop()
    assert wait_for(lambda: not manager.led_is_on()), "LED did not turn off"
    assert not manager.is_running()

    session.start()
    manager.start()
    assert wait_for(manager.led_is_on, timeout=3.0), "LED never turned on after restart"
    assert wait_for(
        lambda: session.last_trial() is not None and session.last_trial().trial_id == 1,
        timeout=3.0,
    ), "restarted session never produced a trial"
    assert wait_for(lambda: session.trial_counter == 1)

    manager.stop()
