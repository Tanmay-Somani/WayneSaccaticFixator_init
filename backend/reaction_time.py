import statistics
from typing import List, Optional

from backend.models import SessionStats, Trial


class ReactionTimeCalculator:
    """Computes session statistics.

    MISS trials are excluded from all reaction-time statistics.
    """

    @staticmethod
    def stats(trials: List[Trial], led_ids: Optional[List[int]] = None) -> SessionStats:
        total = len(trials)
        hits = [t for t in trials if t.is_hit]
        misses = total - len(hits)

        hit_percentage = (len(hits) / total * 100.0) if total else 0.0

        rt_values = [t.reaction_time_ms for t in hits if t.reaction_time_ms is not None]

        per_led: dict = {}
        if led_ids:
            for led_id in led_ids:
                led_trials = [t for t in trials if t.led_id == led_id]
                per_led[led_id] = ReactionTimeCalculator.stats(led_trials)

        if not rt_values:
            return SessionStats(
                total_trials=total,
                hits=len(hits),
                misses=misses,
                hit_percentage=hit_percentage,
                per_led=per_led,
            )

        return SessionStats(
            total_trials=total,
            hits=len(hits),
            misses=misses,
            hit_percentage=hit_percentage,
            avg_rt_ms=statistics.fmean(rt_values),
            median_rt_ms=statistics.median(rt_values),
            min_rt_ms=min(rt_values),
            max_rt_ms=max(rt_values),
            stddev_rt_ms=ReactionTimeCalculator._stdev(rt_values),
            per_led=per_led,
        )

    @staticmethod
    def _stdev(values: List[float]) -> Optional[float]:
        if len(values) < 2:
            return None
        return statistics.stdev(values)
