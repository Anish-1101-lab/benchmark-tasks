# Line up three cans on shelf marks from shortest to tallest

Shelf stocking follows planograms, and many product lines come in one design in several sizes. The robot has to
compare heights and order the cans left to right; they look alike from above, so it has to judge height, not colour.

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
  --instruction "put the cans on the shelf marks from shortest on the left to tallest on the right" --scorer task_score \
  --max-steps 2400 --store-frames --log-dir ~/yam-eval/sort-cans-by-height-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "put the cans on the shelf marks from shortest on the left to tallest on the right" --scorer task_score \
  --max-steps 1000 --store-frames --log-dir ~/yam-eval/sort-cans-by-height-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/sort-cans-by-height-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()` at the
end of the episode. A can is on a mark if it stands upright (within about 25 degrees of vertical), its centre within
the mark's edges and no more than 2 cm above where it rests. 1.0: the 6 cm can is on the left mark, the 9 cm can on
the middle mark and the 12 cm can on the right mark. 0.0 otherwise. There is no partial credit: three cans set on the
marks at random are in order one time in six, and a single can on its right mark one time in three.

| Outcome (`outcome()`) | Situation | Score |
|---|---|---|
| `sorted` | Every can on its mark, shortest left, tallest right | 1.0 |
| `0_placed .. 3_placed` | Any other arrangement (n cans on some mark) | 0.0 |

## The demo

The arms take turns: the left arm puts the 9 cm can on the middle mark and moves aside while the right arm waits at
its ready pose, then the right arm puts the 12 cm can on the right mark and the 6 cm can on the left mark. Each grip
pauses 2.5 s above the can and closes at its mid-height; the right arm aims 1.6 cm left of the left mark to make up
for the short can's slip in its grip.

## Runtime and seeds

- Run limit: 2,400 steps (2 minutes at 20 Hz). The demo finishes in about 36 s of simulated time.
- Runtime per trial on an L40S: about 2.5 minutes for the scripted demo and about 8 minutes for a full
  2,400-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
