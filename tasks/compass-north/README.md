# Put a cube on the pad north of a plate, reading north from a compass card

Site plans, maps and warehouse floors give directions by compass, and north is rarely 'away from the robot'. A robot
that maps north to 'forward' by habit puts things in the wrong place; here it has to read the compass card.

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
  --instruction "put the cube on the pad north of the plate" --scorer task_score \
  --max-steps 1200 --store-frames --log-dir ~/yam-eval/compass-north-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "put the cube on the pad north of the plate" --scorer task_score \
  --max-steps 1000 --store-frames --log-dir ~/yam-eval/compass-north-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/compass-north-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()` at the
end of the episode. The cube is on a pad if its centre is within the pad's edges and no more than 2 cm above where it
rests on the pad. 1.0: the cube is on the pad 11 cm left of the plate (north). 0.0: on any other pad (the far pad is
where 'north is forward' would put it), or anywhere else.

| Outcome (`outcome()`) | Situation | Score |
|---|---|---|
| `north` | On the pad left of the plate | 1.0 |
| `east` | On the far pad | 0.0 |
| `south, west` | On the right or near pad | 0.0 |
| `none` | Anywhere else | 0.0 |

## The demo

The left arm picks up the cube, pausing 2.5 s above it first, and sets it on the pad left of the plate.

## Runtime and seeds

- Run limit: 1,200 steps (1 minute at 20 Hz). The demo finishes in about 10 s of simulated time.
- Runtime per trial on an L40S: about 2.5 minutes for the scripted demo and about 5 minutes for a full
  1,200-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
