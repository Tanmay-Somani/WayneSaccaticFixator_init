from pathlib import Path
from typing import List

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from backend.models import Trial

HIT_COLOR = "#3ba55d"
MISS_COLOR = "#e05353"

plt.rcParams["figure.facecolor"] = "#ffffff"
plt.rcParams["axes.titlesize"] = 12


def _hit_rt(trials: List[Trial]) -> List[float]:
    return [
        t.reaction_time_ms
        for t in trials
        if t.is_hit and t.reaction_time_ms is not None
    ]


def _save(fig, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _empty_text(fig, message: str) -> None:
    ax = fig.add_subplot(111)
    ax.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        fontsize=13,
        color="#666666",
        transform=ax.transAxes,
    )
    ax.set_axis_off()


def plot_reaction_time_series(
    trials: List[Trial], path: Path, response_window_ms: float
) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4))
    if not trials:
        _empty_text(fig, "No trials in this run")
        return _save(fig, path)

    numbers = [t.trial_id for t in trials]
    hit_numbers = [t.trial_id for t in trials if t.is_hit]
    hits_rt = [t.reaction_time_ms for t in trials if t.is_hit]

    ax.plot(
        hit_numbers,
        hits_rt,
        marker="o",
        linestyle="-",
        linewidth=1,
        color=HIT_COLOR,
        markersize=4,
        label="HIT (reaction time)",
    )
    miss_numbers = [t.trial_id for t in trials if not t.is_hit]
    if miss_numbers:
        ax.plot(
            miss_numbers,
            [response_window_ms] * len(miss_numbers),
            marker="X",
            linestyle="None",
            color=MISS_COLOR,
            markersize=7,
            label="MISS (at response window)",
        )

    ax.set_xlabel("Trial")
    ax.set_ylabel("Reaction time (ms)")
    ax.set_title("Reaction Time per Trial")
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.4)
    return _save(fig, path)


def plot_rt_histogram(
    trials: List[Trial], path: Path, response_window_ms: float = None
) -> Path:
    fig, ax = plt.subplots(figsize=(7, 4))
    rt = _hit_rt(trials)
    if not rt:
        _empty_text(fig, "No HIT data in this run")
        return _save(fig, path)

    ax.hist(rt, bins="auto", color=HIT_COLOR, alpha=0.75, edgecolor="#ffffff")
    mean = sum(rt) / len(rt)
    median = sorted(rt)[len(rt) // 2]
    ax.axvline(mean, color="#2b6b40", linestyle="--", label=f"mean {mean:.0f} ms")
    ax.axvline(median, color="#000000", linestyle=":", label=f"median {median:.0f} ms")

    ax.set_xlabel("Reaction time (ms)")
    ax.set_ylabel("Frequency")
    ax.set_title("Reaction Time Distribution (HITs)")
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.4)
    return _save(fig, path)


def plot_hit_miss(
    trials: List[Trial], path: Path, response_window_ms: float = None
) -> Path:
    fig, ax = plt.subplots(figsize=(5, 5))
    if not trials:
        _empty_text(fig, "No trials in this run")
        return _save(fig, path)

    hits = sum(1 for t in trials if t.is_hit)
    misses = len(trials) - hits
    ax.pie(
        [hits, misses],
        labels=[f"HIT ({hits})", f"MISS ({misses})"],
        colors=[HIT_COLOR, MISS_COLOR],
        autopct="%1.1f%%",
        startangle=90,
    )
    ax.set_title("HIT / MISS Breakdown")
    return _save(fig, path)


def plot_cumulative_avg(
    trials: List[Trial], path: Path, response_window_ms: float = None
) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4))
    rt = _hit_rt(trials)
    if not rt:
        _empty_text(fig, "No HIT data in this run")
        return _save(fig, path)

    running = []
    running_sum = 0.0
    for i, value in enumerate(rt, start=1):
        running_sum += value
        running.append(running_sum / i)

    ax.plot(range(1, len(running) + 1), running, marker="o", markersize=3, color=HIT_COLOR)
    ax.set_xlabel("Hit count")
    ax.set_ylabel("Cumulative avg reaction time (ms)")
    ax.set_title("Learning Curve (Cumulative Average RT)")
    ax.grid(True, linestyle=":", alpha=0.4)
    return _save(fig, path)


def plot_led_accuracy(
    trials: List[Trial], path: Path, response_window_ms: float = None
) -> Path:
    """Per-LED hit percentage bar chart — shows which targets are easiest
    and hardest for the user."""
    fig, ax = plt.subplots(figsize=(8, 4))
    if not trials:
        _empty_text(fig, "No trials in this run")
        return _save(fig, path)

    led_ids = sorted({t.led_id for t in trials})
    labels = [f"LED {i}" for i in led_ids]
    accuracies = []
    counts = []
    for led_id in led_ids:
        led_trials = [t for t in trials if t.led_id == led_id]
        hits = sum(1 for t in led_trials if t.is_hit)
        accuracies.append(hits / len(led_trials) * 100.0 if led_trials else 0.0)
        counts.append(len(led_trials))

    bars = ax.bar(labels, accuracies, color=HIT_COLOR, alpha=0.85, edgecolor="#ffffff")
    ax.axhline(100.0, color="#999999", linestyle="--", linewidth=0.8)
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 2,
            f"{count}",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#666666",
        )

    ax.set_xlabel("Target LED")
    ax.set_ylabel("Hit accuracy (%)")
    ax.set_title("Accuracy per LED")
    ax.set_ylim(0, 112)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    return _save(fig, path)


def plot_tap_map(
    trials: List[Trial],
    path: Path,
    response_window_ms: float = None,
    led_positions: List[dict] = None,
) -> Path:
    """Scatter of where the user actually tapped, overlaid on the LED ring.

    Correct taps land on their target; wrong taps drift toward the
    neighbouring light they pressed instead. ``led_positions`` draws the
    full board geometry (all 33 lights) as reference markers. Coordinates
    are normalized (0..1) so the map matches the board layout exactly."""
    fig, ax = plt.subplots(figsize=(7, 7))

    if led_positions:
        xs = [p["x"] for p in led_positions]
        ys = [p["y"] for p in led_positions]
        ax.scatter(
            xs,
            ys,
            marker="o",
            s=26,
            color="#444444",
            alpha=0.9,
            zorder=1,
            linewidths=0.6,
            edgecolors="#ffffff",
        )
        for p in led_positions:
            ax.annotate(
                str(p["id"]),
                (p["x"], p["y"]),
                fontsize=6,
                ha="center",
                va="center",
                color="#ffffff",
            )

    hit_x, hit_y = [], []
    wrong_x, wrong_y = [], []
    for t in trials:
        if t.touch_x is None or t.touch_y is None:
            continue
        if t.is_hit:
            hit_x.append(t.touch_x)
            hit_y.append(t.touch_y)
        else:
            wrong_x.append(t.touch_x)
            wrong_y.append(t.touch_y)

    if hit_x:
        ax.scatter(hit_x, hit_y, s=70, color=HIT_COLOR, alpha=0.6, zorder=3, label="HIT tap")
    if wrong_x:
        ax.scatter(wrong_x, wrong_y, s=70, color=MISS_COLOR, alpha=0.6, zorder=3, label="wrong tap")

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Normalized x")
    ax.set_ylabel("Normalized y")
    ax.set_title("Tap Position Map over LED Ring")
    ax.set_aspect("equal")
    if hit_x or wrong_x:
        ax.legend()
    ax.grid(True, linestyle=":", alpha=0.4)
    return _save(fig, path)
