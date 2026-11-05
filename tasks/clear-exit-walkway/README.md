# Clear the boxes off a marked walkway to an emergency exit

Blocked exit routes are among the most cited workplace fire-safety violations. A robot tidying a warehouse or office
should know that a marked exit walkway has to be clear, without being told which boxes to move or where.

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
  --instruction "move the boxes off the walkway to the emergency exit" --scorer task_score \
  --max-steps 2400 --store-frames --log-dir ~/yam-eval/clear-exit-walkway-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "move the boxes off the walkway to the emergency exit" --scorer task_score \
  --max-steps 1000 --store-frames --log-dir ~/yam-eval/clear-exit-walkway-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/clear-exit-walkway-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()` at the
end of the episode. A box blocks the walkway if its centre is within 10.2 cm of the midline and between the arms'
midpoint and 50 cm forward (the walkway plus half a box and 1.2 cm of margin all round). A box is lost if it has
fallen off the table. 1.0: no box blocks the walkway and none is lost. 0.5: exactly one box blocks it and none is
lost. 0.0: two or more block it, or any box is lost.

| Outcome (`outcome()`) | Situation | Score |
|---|---|---|
| `0_blocking` | No box over the walkway, none off the table | 1.0 |
| `1_blocking` | One box over it, none off the table | 0.5 |
| `2_blocking, 3_blocking` | Two or three over it | 0.0 |
| `lost` | Any box fallen off the table | 0.0 |

## The demo

The arms take turns: the left arm sets the near box down 17 cm left of the midline while the right arm waits at its
ready pose, then the right arm sets the far box down 18 cm right of it. Each grip pauses 2.5 s above the box first.

## Runtime and seeds

- Run limit: 2,400 steps (2 minutes at 20 Hz). The demo finishes in about 24 s of simulated time.
- Runtime per trial on an L40S: about 2.5 minutes for the scripted demo and about 8 minutes for a full
  2,400-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
