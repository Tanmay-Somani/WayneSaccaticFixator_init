from datetime import datetime, timezone

from backend.models import Trial
from backend.reaction_time import ReactionTimeCalculator


def _trial(hit_miss, rt, led_id=1):
    return Trial(
        trial_id=1,
        user_id="u",
        system_time=datetime.now(timezone.utc).isoformat(),
        led_id=led_id,
        led_on_timestamp=1,
        touch_timestamp=2 if hit_miss == "HIT" else None,
        reaction_time_ms=rt,
        waiting_time_ms=0.0,
        hit_miss=hit_miss,
    )


def test_stats_excludes_misses():
    trials = [
        _trial("HIT", 200),
        _trial("HIT", 300),
        _trial("HIT", 1000),
        _trial("MISS", None),
        _trial("MISS", None),
    ]
    stats = ReactionTimeCalculator.stats(trials)

    assert stats.total_trials == 5
    assert stats.hits == 3
    assert stats.misses == 2
    assert stats.hit_percentage == 60.0
    assert stats.avg_rt_ms == 500.0
    assert stats.median_rt_ms == 300.0
    assert stats.min_rt_ms == 200.0
    assert stats.max_rt_ms == 1000.0
    assert stats.stddev_rt_ms is not None


def test_stats_empty():
    stats = ReactionTimeCalculator.stats([])
    assert stats.total_trials == 0
    assert stats.hits == 0
    assert stats.misses == 0
    assert stats.hit_percentage == 0.0
    assert stats.avg_rt_ms is None
    assert stats.median_rt_ms is None
    assert stats.stddev_rt_ms is None


def test_stats_only_misses():
    stats = ReactionTimeCalculator.stats([_trial("MISS", None), _trial("MISS", None)])
    assert stats.total_trials == 2
    assert stats.hits == 0
    assert stats.misses == 2
    assert stats.hit_percentage == 0.0
    assert stats.avg_rt_ms is None


def test_single_hit_has_no_stddev():
    stats = ReactionTimeCalculator.stats([_trial("HIT", 250)])
    assert stats.avg_rt_ms == 250.0
    assert stats.min_rt_ms == 250.0
    assert stats.max_rt_ms == 250.0
    assert stats.median_rt_ms == 250.0
    assert stats.stddev_rt_ms is None


def test_per_led_stats_breakdown():
    trials = [
        _trial("HIT", 200, led_id=1),
        _trial("HIT", 300, led_id=1),
        _trial("MISS", None, led_id=1),
        _trial("HIT", 400, led_id=2),
        _trial("MISS", None, led_id=3),
    ]
    stats = ReactionTimeCalculator.stats(trials, led_ids=[1, 2, 3])

    assert stats.total_trials == 5
    assert stats.hits == 3
    assert stats.misses == 2

    led1 = stats.per_led[1]
    assert led1.total_trials == 3
    assert led1.hits == 2
    assert led1.misses == 1
    assert led1.hit_percentage == 2 / 3 * 100.0
    assert led1.avg_rt_ms == 250.0

    led2 = stats.per_led[2]
    assert led2.total_trials == 1
    assert led2.hits == 1
    assert led2.avg_rt_ms == 400.0

    led3 = stats.per_led[3]
    assert led3.total_trials == 1
    assert led3.hits == 0
    assert led3.avg_rt_ms is None

    payload = stats.to_dict()
    assert set(payload["per_led"].keys()) == {"1", "2", "3"}
    assert payload["per_led"]["1"]["hits"] == 2


def test_per_led_without_led_ids_is_empty():
    stats = ReactionTimeCalculator.stats([_trial("HIT", 200)])
    assert stats.per_led == {}
