# Kit the two 8 cm spacers for a robot joint by measuring against a ruler

Five steel spacers lie side by side on a parts tray, their near ends lined up at the zero of a printed centimetre
ruler. They differ only in length: 10, 8, 6, 12 and 8 cm, left to right. The robot has to put both 8 cm spacers, and
nothing else, in the blue kit cup behind the tray. `task.py` checks when it loads that exactly two spacers are 8 cm.

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
  --instruction "put the two 8 cm spacers in the kit cup" --scorer task_score \
  --max-steps 2400 --store-frames --log-dir ~/yam-eval/spacer-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "put the two 8 cm spacers in the kit cup" --scorer task_score \
  --max-steps 1000 --store-frames --log-dir ~/yam-eval/spacer-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/spacer-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()`
at the end of the episode. A spacer is in the cup when its centre is inside the cup's walls, below their tops.

| Outcome (`outcome()`) | Cup holds | Score |
|---|---|---|
| `exact` | Both 8 cm spacers and nothing else (all still) | 1.0 |
| `one` | One 8 cm spacer and nothing else | 0.0 |
| `wrong` | Any spacer that isn't 8 cm | 0.0 |
| `empty` | Nothing | 0.0 |

There is no partial credit: a random spacer is 8 cm two times in five, so a half score would reward guessing; a
random pair is right one time in ten. In the real world, scoring is a look into the cup.

## The demo

The arms take turns: the left arm puts the 8 cm spacer second from the left in the cup and moves aside while the
right arm waits at its ready pose, then the right arm puts the rightmost one in. The spacers lie on a 3 cm tray so the
fingers can close around a 2 cm bar without meeting the table; each grab pauses 2.5 s above the spacer first.

## Runtime and seeds

- Run limit: 2,400 steps (2 minutes at 20 Hz). The demo finishes in about 28 s of simulated time.
- Runtime per trial on an L40S: about 2.5 minutes for the scripted demo and about 8 minutes for a full
  2,400-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
