# Fill a weekly pill organizer for Monday, Wednesday and Friday

A weekly pill organizer with seven compartments, labelled M T W T F S S, is fixed to the table; three tablets lie on
a small tray in front of the arms. The user asks for one tablet in each of the Monday, Wednesday and Friday
compartments. The robot has to read the day labels (two of the letters, T and S, appear twice), place exactly one
tablet per requested day, and put nothing in the other days.

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
  --instruction "put one tablet in each of the monday, wednesday and friday compartments" --scorer task_score \
  --max-steps 2400 --store-frames --log-dir ~/yam-eval/pill-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "put one tablet in each of the monday, wednesday and friday compartments" --scorer task_score \
  --max-steps 1200 --store-frames --log-dir ~/yam-eval/pill-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/pill-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()`
at the end of the episode. A tablet is in a compartment when its centre is inside that compartment's walls, below
their tops.

| Outcome (`outcome()`) | Condition | Score |
|---|---|---|
| `wrong_day` | Any tablet in Tuesday, Thursday, Saturday or Sunday | 0.0 |
| `3_of_3` | Monday, Wednesday and Friday each hold exactly one tablet (and all are still) | 1.0 |
| `2_of_3` | Two of the three hold exactly one tablet | 0.67 |
| `1_of_3` | One of the three holds exactly one tablet | 0.33 |
| `0_of_3` | None does: nothing placed, or only double doses | 0.0 |

A requested day with two or three tablets (a double dose) earns nothing for that day. Tablets left on the tray,
the table, the label strip or a wall top don't count. In the real world, scoring is a look into each compartment.

## The demo

The arms take turns so they never reach into the middle together (when they did, they collided and both grabs
failed). The left arm puts one tablet in Monday and one in Wednesday and moves aside while the right arm waits at
its ready pose; then the right arm puts the third in Friday. Each grab pauses 2.5 s above the caplet first. The
tablets sit on a 3 cm tray so the fingers can close on an 8 mm caplet without meeting the table.

## Runtime and seeds

- Run limit: 2,400 steps (2 minutes at 20 Hz). The demo finishes in about 40 s of simulated time.
- Runtime per trial on an L40S: about 3 minutes for the scripted demo and about 8 minutes for a full
  2,400-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
