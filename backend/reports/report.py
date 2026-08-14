from pathlib import Path
from typing import List

from backend.models import Trial
from backend.reaction_time import ReactionTimeCalculator
from backend.reports import exporter, graph

GRAPH_FILENAMES = {
    "plot_reaction_time_series": "reaction_time_series.png",
    "plot_rt_histogram": "rt_histogram.png",
    "plot_hit_miss": "hit_miss_pie.png",
    "plot_cumulative_avg": "cumulative_avg_rt.png",
    "plot_led_accuracy": "led_accuracy.png",
    "plot_tap_map": "tap_map.png",
}


def generate_run_report(
    user_id: str,
    session_id: str,
    trials: List[Trial],
    response_window_ms: int,
    output_dir,
    led_positions: List[dict] = None,
) -> dict:
    """Write CSV, summary JSON, and PNG graphs for one run into
    ``output_dir/<user_id>/<session_id>/``. Returns a dict describing the
    generated report."""
    run_dir = Path(output_dir) / user_id / session_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if led_positions:
        led_ids = [p["id"] for p in led_positions]
    else:
        led_ids = sorted({t.led_id for t in trials})
    stats = ReactionTimeCalculator.stats(trials, led_ids=led_ids)

    csv_path = exporter.write_csv(trials, run_dir / "run_data.csv")
    summary_path = exporter.write_summary_json(
        user_id, session_id, trials, stats, run_dir / "summary.json"
    )

    graphs_dir = run_dir / "graphs"
    generated_files = {
        "csv": str(csv_path),
        "summary": str(summary_path),
        "graphs": [],
    }

    plot_functions = [
        graph.plot_reaction_time_series,
        graph.plot_rt_histogram,
        graph.plot_hit_miss,
        graph.plot_cumulative_avg,
        graph.plot_led_accuracy,
        graph.plot_tap_map,
    ]
    for plot_fn in plot_functions:
        filename = GRAPH_FILENAMES[plot_fn.__name__]
        if plot_fn is graph.plot_tap_map:
            file_path = plot_fn(
                trials, graphs_dir / filename, response_window_ms, led_positions=led_positions
            )
        else:
            file_path = plot_fn(trials, graphs_dir / filename, response_window_ms)
        generated_files["graphs"].append(str(file_path))

    return {
        "user_id": user_id,
        "session_id": session_id,
        "path": str(run_dir),
        "files": generated_files,
    }
