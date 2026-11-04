# Spend exactly 10 euros: put the items whose prices add up to 10 in the basket

Four grocery boxes stand in a row, each with a shelf price tag in front of it: 6, 3, 2 and 7 euros, left to right.
A basket stands behind them. The user asks to spend exactly 10 euros. Only one set of items adds up to 10, the 3 and
the 7 (`task.py` checks this when it loads), so the robot has to read the prices and add them up.

| File | What it is |
|---|---|
| `task.py` | The task file: objects, `success()`, `score()`, `outcome()` and the scripted `demo()` |

## Run a trial

On a Brev instance set up by the Robocurve launchable (Isaac Lab-Arena, the `yam_arena` embodiment, Dream-1),
from this folder (if your shell's start-up changes directory, pass the full path to `task.py`):

```bash
# Dream-1
inspect-robots run --embodiment yam_arena --policy dream \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "spend exactly 10 euros: put items in the basket so their prices add up to exactly 10" \
  --scorer task_score --max-steps 2400 --store-frames --log-dir ~/yam-eval/budget-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "spend exactly 10 euros: put items in the basket so their prices add up to exactly 10" \
  --scorer task_score --max-steps 1000 --store-frames --log-dir ~/yam-eval/budget-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/budget-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()`
at the end of the episode. An item is in the basket when its centre is inside the basket's walls, below their tops.

| Outcome (`outcome()`) | Basket holds | Score |
|---|---|---|
| `exact` | Exactly green (3) and orange (7) | 1.0 |
| `half` | Only green, or only orange | 0.0 |
| `empty` | Nothing | 0.0 |
| `wrong` | Any other item (yellow 6 or blue 2), with or without the right ones | 0.0 |

There is no partial credit: one item picked at random would be the 3 or the 7 half the time, so a half score would
reward guessing. `outcome()` still reports `half` separately, for analysis. Taking everything, the cheapest items or
a random pair all score 0. In the real world, scoring is a look into the basket.

## The demo

The arms take turns: the left arm puts the green item (3) in the basket and moves aside while the right arm waits at
its ready pose, then the right arm puts the orange item (7) in. Each grab pauses 2.5 s above the item first.

## Runtime and seeds

- Run limit: 2,400 steps (2 minutes at 20 Hz). The demo finishes in about 28 s of simulated time.
- Runtime per trial on an L40S: about 2.5 minutes for the scripted demo; the Dream-1 run that reached 1.0 took
  about 5 minutes including Isaac Sim start-up (a full 2,400-step run takes about 8).
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
