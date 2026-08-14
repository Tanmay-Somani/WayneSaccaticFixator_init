# Saccadic Fixator — 33-Light Radial Board

A software prototype of a **Saccadic Fixator** reaction-time system: a 33-LED
radial board with a single touch input, monotonic high-resolution timing,
per-run data exports, and a modular architecture designed to grow without
rewriting the core trial logic.

## Features

- **33-LED radial board** arranged on 16 spokes (3→1 light pattern) plus a
  center target, matching the physical Wayne Saccadic Fixator geometry.
- **True saccade forcing** — every trial selects the next target uniformly at
  random, with no immediate repeat, so the user must make a genuine eye
  movement to the stimulus.
- **Coordinate-based touch scoring** — taps map to the nearest LED; hits,
  wrong touches, and timeouts (misses) are recorded precisely.
- **Monotonic high-resolution timing** (`time.monotonic_ns()`).
- **Per-run reports** — CSV/JSON exports plus matplotlib graphs.
- **Sharp, responsive LED board** — pixel-perfect, device-pixel-ratio-aware
  canvas rendering that scales fluidly from phones to 4K displays.

## Stack

- **Backend:** Python + Flask
- **Database:** SQLite (stdlib `sqlite3`)
- **Frontend:** vanilla HTML + CSS + JavaScript (no frameworks)
- **Reports:** matplotlib (PNG graphs) + CSV/JSON exports

## Quick start

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`, press **START TEST**, then tap the LED that
lights up red. The lit LED has a 3-second response window (configurable in
`config.py`); a trial with no correct tap within the window is recorded as a
MISS. Press **STOP TEST** to end the run and generate the report.

### Run the tests

```bash
python -m pytest
```

## How a trial works

```
pick a random target LED -> turn that LED ON (red) -> record LED_ON timestamp
-> wait for touch | timeout -> LED OFF -> save -> next trial immediately
```

- **HIT** — the tap maps to the lit target; reaction time = touch − LED-on.
- **WRONG TOUCH** — the tap maps to another LED; ignored and counted, the
  trial keeps waiting.
- **MISS** — timeout with no correct tap; no reaction time is recorded.
- Miss trials are excluded from all reaction-time statistics.
- The next target is chosen uniformly at random from the 33 LEDs and never
  repeats the LED that was just tapped.

## The board layout

The 16 spokes radiate at 22.5° intervals; spoke 1 sits at the top and
numbering runs clockwise. Spokes alternate **3 → 1** lights stacked outward.
On a 3-light spoke the LEDs sit at the inner, middle, and outer radii; on a
1-light spoke the single LED sits on the outer radius only, so the outer
ring is complete (16 LEDs) while the middle and inner rings have 8 each.
The center light (S33) is a target like any other.

Total: 16 outer + 8 middle + 8 inner + 1 center = **33 lights**.

## Architecture

```
backend/
  timer.py           # high-resolution monotonic clock
  models.py          # User, Trial, SessionStats
  led.py             # LED + LEDArray (nearest-LED mapping, random target)
  input.py           # input abstraction (input_id configurable)
  trial_manager.py   # core trial loop (background thread)
  reaction_time.py   # session statistics
  session.py         # session state + aggregates
  database.py        # SQLite schema + CRUD
  reports/
    exporter.py      # run_data.csv + summary.json
    graph.py         # matplotlib chart functions
    report.py        # per-run report orchestration
app.py               # Flask routes (API + static frontend)
config.py            # board geometry + runtime settings
static/              # HTML / CSS / JS frontend (canvas LED board)
```

The core trial loop never hard-codes a single device; changing board geometry
only means editing the layout in `config.py`.

## API

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET    | `/` | Frontend |
| POST   | `/api/session/start` | Start a run (creates a session id) |
| POST   | `/api/session/stop` | Stop the run and generate the report |
| POST   | `/api/touch` | Simulated touch input (`{"x": 0..1, "y": 0..1}`) |
| GET    | `/api/state` | Live state (active LED, positions, trial, stats) |
| GET    | `/api/stats` | Session statistics (overall + per LED) |
| GET    | `/api/trials` | Recent trials (`?user_id=&limit=`) |

## Per-run reports

When a run stops, a report is written to
`output/<user_id>/<session_id>/`:

```
run_data.csv                # raw trial records (CSV)
summary.json                # session statistics + per-LED breakdown
graphs/
  reaction_time_series.png  # RT per trial, misses marked at the window
  rt_histogram.png          # HIT RT distribution (mean/median)
  hit_miss_pie.png          # HIT vs MISS breakdown
  cumulative_avg_rt.png     # learning curve
  led_accuracy.png          # hit accuracy per LED
  tap_map.png               # scatter of where the user actually tapped
```

`run_data.csv` columns: `trial_id, session_id, user_id, system_time, led_id,
led_on_timestamp, touch_timestamp, reaction_time_ms, waiting_time_ms,
hit_miss, touch_led_id, touch_x, touch_y, wrong_touch_count`.

## Configuration

Settings live in `config.py`:

| Setting | Default | Description |
| ------- | ------- | ----------- |
| `LED_SPOKES` | `16` | Number of radial spokes |
| `LED_RADII` | `(0.18, 0.32, 0.46)` | Per-LED stack radii in normalized units |
| `LED_SPOKE_PATTERN` | `(3, 1)` | LEDs per spoke, alternating |
| `INPUT_ID` | `1` | Input identifier |
| `RESPONSE_WINDOW_MS` | `3000` | Max response window per trial |
| `USER_ID` | `demo-user` | Current user |
| `DATABASE_PATH` | `data/saccadic_fixator.db` | SQLite file |
| `OUTPUT_DIR` | `output/` | Per-run report output |

`build_led_layout()` generates the 33-light radial layout automatically;
change `LED_SPOKES` / `LED_RADII` / `LED_SPOKE_PATTERN` to reshape the board
without touching any other code.

## Known limitations

- Touch timestamps include ~1–5 ms of localhost HTTP latency; a real
  hardware input path (e.g. GPIO interrupt) will timestamp at the device
  level.
- Report generation runs synchronously on Stop.
- No report viewer in the UI yet.
