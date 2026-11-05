# Load a part onto the machine whose stack light shows it's ready

Machine tending is a large share of factory robot work, and stack lights (red: stopped or fault, amber: warning,
green: ready or running) are how machines report their state on the shop floor. The robot is told only to load the
machine that is ready, so it has to read the lights and know the convention.

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
  --instruction "load the part onto the machine that is ready" --scorer task_score \
  --max-steps 1200 --store-frames --log-dir ~/yam-eval/load-ready-machine-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "load the part onto the machine that is ready" --scorer task_score \
  --max-steps 1000 --store-frames --log-dir ~/yam-eval/load-ready-machine-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/load-ready-machine-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()` at the
end of the episode. The part is on a fixture if its centre is within the fixture's edges (5 cm of its centre, forward
and sideways) and no more than 2 cm above where it rests on the fixture. 1.0: the part is on the left machine's
fixture (green light). 0.0: on the middle (red) or right (amber) fixture, or anywhere else.

| Outcome (`outcome()`) | Situation | Score |
|---|---|---|
| `m_left` | On the left fixture (green: ready) | 1.0 |
| `m_middle` | On the middle fixture (red) | 0.0 |
| `m_right` | On the right fixture (amber) | 0.0 |
| `none` | Anywhere else | 0.0 |

## The demo

The left arm picks up the part, pausing 2.5 s above it first, and sets it on the left machine's fixture.

## Runtime and seeds

- Run limit: 1,200 steps (1 minute at 20 Hz). The demo finishes in about 10 s of simulated time.
- Runtime per trial on an L40S: about 2.5 minutes for the scripted demo and about 5 minutes for a full
  1,200-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
