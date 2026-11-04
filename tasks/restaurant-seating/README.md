# Seat two parties at the tables with the right number of chairs

A scale-model dining floor: four tables in a 2 x 2 grid with 2, 3, 4 and 5 chairs around them, and a red and a blue
reservation marker in front of the arms. The host's instruction puts red on the table with 4 chairs and blue on the
table with 2. The robot has to count the chairs at each table; the nearest table, the biggest group of chairs or a
guess won't do.

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
  --instruction "seat the parties: put the red marker on the table with 4 chairs and the blue marker on the table with 2 chairs" \
  --scorer task_score --max-steps 2400 --store-frames --log-dir ~/yam-eval/rest-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "seat the parties: put the red marker on the table with 4 chairs and the blue marker on the table with 2 chairs" \
  --scorer task_score --max-steps 1000 --store-frames --log-dir ~/yam-eval/rest-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/rest-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()`
at the end of the episode. A marker is on a table when its centre is over the table top and its bottom is within
1 cm of it.

| Outcome (`outcome()`) | Condition | Score |
|---|---|---|
| `seated` | Red on the near-right table (4 chairs) and blue on the far-left table (2 chairs), both still | 1.0 |
| `red_only` / `blue_only` | Only one marker on its table | 0.0 |
| `neither` | Anything else, including doing nothing | 0.0 |

There is no partial credit: a marker put on a random table is right one time in four, so a half score would reward
guessing; both right by chance is one in twelve. `outcome()` still reports one-of-two separately, for analysis.
`task.py` checks when it loads that the four tables have 2, 3, 4 and 5 chairs and that the targets have 4 and 2.

| Table | Chairs |
|---|---|
| Far left | 2 (target for blue) |
| Far right | 3 |
| Near left | 5 |
| Near right | 4 (target for red) |

## The demo

The arms take turns: the left arm puts the blue marker on the far-left table and moves aside while the right arm
waits at its ready pose, then the right arm puts the red marker on the near-right table. Each grab pauses 2.5 s
above the marker first.

## Runtime and seeds

- Run limit: 2,400 steps (2 minutes at 20 Hz). The demo finishes in about 28 s of simulated time.
- Runtime per trial on an L40S: about 2.5 minutes for the scripted demo and about 8 minutes for a full
  2,400-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
