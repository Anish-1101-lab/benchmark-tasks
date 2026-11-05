# Tag the pressure gauge that reads in its red zone

Inspection rounds in plants and utilities come down to reading gauges and flagging the ones out of range. The three
gauges here are alike except for where the needle points, so the robot has to read each dial against its red zone.

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
  --instruction "put the red tag in front of the gauge reading in the red zone" --scorer task_score \
  --max-steps 1200 --store-frames --log-dir ~/yam-eval/gauge-red-zone-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "put the red tag in front of the gauge reading in the red zone" --scorer task_score \
  --max-steps 1000 --store-frames --log-dir ~/yam-eval/gauge-red-zone-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/gauge-red-zone-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()` at the
end of the episode. The tag is on a spot if its centre is within the spot's edges and no more than 2 cm above where it
rests on the spot. 1.0: the tag is on the spot in front of the left gauge (the one in the red). 0.0: on another spot,
or anywhere else.

| Outcome (`outcome()`) | Situation | Score |
|---|---|---|
| `g_left` | On the left gauge's spot (in the red) | 1.0 |
| `g_middle, g_right` | On another gauge's spot | 0.0 |
| `none` | Anywhere else | 0.0 |

## The demo

The left arm picks up the tag, pausing 2.5 s above it first, and sets it on the left gauge's tag spot.

## Runtime and seeds

- Run limit: 1,200 steps (1 minute at 20 Hz). The demo finishes in about 10 s of simulated time.
- Runtime per trial on an L40S: about 2.5 minutes for the scripted demo and about 5 minutes for a full
  1,200-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
