# Saccadic Fixator 

A portable Saccadic-Fixator-style reaction-time system. This is the current
software prototype: a **33-LED radial board, one touch input**, accurate
monotonic timing, per-run data exports, and a modular architecture designed
to grow without rewriting the core trial logic.

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

Open `http://127.0.0.1:5000`, press **Start**, then tap the LED that lights
up red. The lit LED has a 3-second response window (configurable) — no correct
tap within the window is recorded as a MISS. Press **Stop** to end the run.

### Run the tests

```bash
python -m pytest
```

## The board — 33 lights in a radial ring

The board is a black square that fills most of the page (70–80% of the
viewport). The 33 lights are arranged radially on **16 spokes**:

```
                     S1 (top)
                  │  │  │
            S16   │  │  │   S2
             ●    │  │  │    ●
             │    │  │  │    │
      S15 ●──┴────┴──┼──┴────┴──● S3
                   S33 (center)
      S14 ●──┬────┬──┼──┬────┬──● S4
             │    │  │  │    │
            S13   │  │  │   S5
                  │  │  │
                     S9 (bottom)
```

- **16 spokes** radiate from the center at 22.5° intervals; spoke 1 is at
  the top (12 o'clock), numbering runs clockwise.
- Spokes alternate **3 → 1 → 3 → 1** lights stacked outward from the center.
- On a **3-light spoke**, the LEDs sit at the inner, middle and outer radii.
- On a **1-light spoke**, the single LED sits on the **outer radius only** —
  so the outer ring is complete (16 LEDs) while the middle and inner rings
  have 8 LEDs each.
- The **center light (S33)** is a target like any other.

Total: 16 outer + 8 middle + 8 inner + 1 center = **33 lights**, matching
the physical Wayne Saccadic Fixator.

## How a trial works

```
pick a random target LED -> turn that LED ON (red) -> record LED_ON
timestamp (monotonic) -> wait -> touch | timeout -> LED OFF -> save ->
next trial immediately with a NEW random LED
```

### The random target function (the heart of the fixator)

The core of the device is the **random selection of the next LED**. Instead of
a predictable sequence, every trial picks the next target uniformly at random
from the 33 lights (`LEDArray.random_led_id()` in `backend/led.py`). This is
what makes the user **saccade** — they cannot anticipate where the next light
will appear, so every trial forces a genuine eye movement to the stimulus.

- The target changes **on every single trial**; trials run back-to-back with
  no fixed pattern.
- Selection is uniform, so over a session every LED receives roughly the same
  share of trials (verified by `test_random_targets_spread_across_leds`).
- **No immediate repeat:** the LED that was just tapped is excluded for the
  next single pick — it cannot be re-lit back-to-back, so the user always has
  to move their eyes. The exclusion lasts one pick only: once a different LED
  becomes the target, the excluded one is back in the pool
  (`random_led_id(exclude=...)`).
- Only the randomly chosen LED lights up; the other 32 stay dark. On the next
  trial the target is re-rolled — it may jump across the board or land on a
  neighbour, but never on the one just touched.

### Touch handling (coordinate-based)

The touch target covers the whole board. Every tap is mapped to the **nearest
LED** by normalized distance (x, y ∈ 0..1).

- **HIT:** the tap maps to the lit target LED → `REACTION_TIME_MS = TOUCH_TIMESTAMP - LED_ON_TIMESTAMP`.
- **WRONG TOUCH:** the tap maps to a different LED → ignored, counted in
  `wrong_touch_count`, and the trial keeps waiting for the correct tap.
- **MISS:** timeout with no correct tap → `TOUCH_TIMESTAMP = NULL`,
  `REACTION_TIME_MS = NULL`.

There is **no random waiting period** in this MVP. The next trial starts
immediately after the current one ends. `WAITING_TIME_MS` is stored (`0`) but
no waiting logic exists yet.

### LED colour

The "on" state is **red** — the lit stimulus glows red on the board (CSS
`--led-on` family in `static/style.css`), and the status pill shows
`● STIMULUS` in red while a trial is live.

All timing uses a **monotonic high-resolution timer** (`time.monotonic_ns()`).
`SYSTEM_TIME` is only a wall-clock record of when the trial occurred.

## Architecture

```
backend/
  timer.py           # high-resolution monotonic clock
  models.py          # User, Trial, SessionStats
  led.py             # LED (single light) + LEDArray (board, nearest-LED mapping, random target)
  input.py           # Input abstraction (input_id configurable)
  trial_manager.py   # core trial loop (background thread)
  reaction_time.py   # session statistics (misses excluded from RT stats)
  session.py         # session state + aggregates
  database.py        # SQLite schema + CRUD
  reports/
    exporter.py      # run_data.csv + summary.json
    graph.py         # one matplotlib chart function per graph
    report.py        # orchestrates a per-run report
app.py               # Flask routes (API + static frontend)
config.py            # LED_SPOKES, LED_RADII, LED_SPOKE_PATTERN, LED_LAYOUT, ...
```

### `led.py` — LED and LEDArray

- `LED` models one light with a normalized `(x, y)` position.
- `LEDArray` owns the whole board: exactly one light can be on at a time, it
  exposes `random_led_id()` for the random target and `nearest_led(x, y)` to
  score touches against the board.

LED and input are identified by configurable ids. The core trial loop never
hard-codes a single device, so changing the board geometry only means editing
the layout in `config.py`, not rewriting trial logic.

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
output/
  <user_id>/
    <session_id>/            # e.g. 2026-08-14_18-31-31
      run_data.csv           # raw trial records (CSV)
      summary.json           # session statistics + per-LED breakdown
      graphs/
        reaction_time_series.png   # RT per trial, misses marked at the window
        rt_histogram.png           # HIT RT distribution (mean/median)
        hit_miss_pie.png           # HIT vs MISS breakdown
        cumulative_avg_rt.png      # learning curve (cumulative average RT)
        led_accuracy.png           # hit accuracy per LED (hardest vs easiest target)
        tap_map.png                # scatter of where the user actually tapped
```

`run_data.csv` columns:

```
trial_id, session_id, user_id, system_time, led_id, led_on_timestamp,
touch_timestamp, reaction_time_ms, waiting_time_ms, hit_miss,
touch_led_id, touch_x, touch_y, wrong_touch_count
```

`led_id` is the randomly selected target for that trial; `touch_led_id`,
`touch_x`, `touch_y` record what the user actually pressed (empty for MISS).

## Session statistics

Total trials, hits, misses, hit percentage, average / median / minimum /
maximum reaction time, and reaction-time standard deviation.
**MISS trials are excluded from all reaction-time statistics.**
Each of these is also computed **per LED** in `stats.per_led`, so you can see
which targets the user handles best and worst.

## Configuration (`config.py`)

| Setting | Default | Description |
| ------- | ------- | ----------- |
| `LED_SPOKES` | `16` | Number of radial spokes (LED 1 on top, clockwise) |
| `LED_RADII` | `(0.18, 0.32, 0.46)` | Per-LED stack radii in normalized board units |
| `LED_SPOKE_PATTERN` | `(3, 1)` | LEDs per spoke, alternating 3 → 1 |
| `LED_LAYOUT` | 33 lights | Auto-generated `{id, x, y, spoke}` positions |
| `INPUT_ID` | `1` | Input identifier |
| `RESPONSE_WINDOW_MS` | `3000` | Max response window per trial |
| `USER_ID` | `demo-user` | Current user |
| `DATABASE_PATH` | `data/saccadic_fixator.db` | SQLite file |
| `OUTPUT_DIR` | `output/` | Per-run report output |

`build_led_layout()` lays the LEDs out on a 16-spoke radial pattern
(3 → 1 → 3 → 1 lights per spoke, single-LED spokes on the outer radius only,
center light last = id 33). Change `LED_SPOKES`/`LED_RADII`/
`LED_SPOKE_PATTERN` to reshape the board — no code changes elsewhere are
needed.

## Database schema

Every trial creates one record in the `trials` table:

```
id, trial_id, user_id, system_time, led_id, led_on_timestamp,
touch_timestamp, reaction_time_ms, waiting_time_ms, hit_miss, session_id,
touch_led_id, touch_x, touch_y, wrong_touch_count
```

`session_id` groups trials from the same run. An existing database is
auto-migrated (`ALTER TABLE ... ADD COLUMN` for `session_id`,
`touch_led_id`, `touch_x`, `touch_y`, `wrong_touch_count`).

## Not part of this MVP

Random delay generation, adaptive difficulty, AI, eye tracking, camera,
autism-specific algorithms, cloud services, patient profiles, therapist
dashboards, and advanced analytics are all future stages. The architecture
leaves room for each.

## Known limitations

- The touch timestamp includes ~1–5 ms of localhost HTTP latency. This
  disappears once a real hardware input path timestamps at the device level
  (e.g. GPIO interrupt).
- Report generation runs synchronously on Stop; it may move to a background
  task if runs get large.
- No report viewer in the UI yet — reports register in the backend only.
