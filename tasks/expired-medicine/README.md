# Put the expired medicines in the return bin, given today's date

Three identical white medicine boxes stand in a line in front of the arms, each with its expiry date (MM/YY) on a
card beside it: 05/26, 02/27 and 09/25. A grey return bin stands on the left. The instruction gives today's date,
November 2026, and asks for every expired box in the bin. The robot has to read the dates and compare them with
today: 05/26 and 09/25 have expired, 02/27 has not.

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
  --instruction "it is november 2026. put every expired medicine box in the return bin" --scorer task_score \
  --max-steps 2400 --store-frames --log-dir ~/yam-eval/med-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "it is november 2026. put every expired medicine box in the return bin" --scorer task_score \
  --max-steps 1000 --store-frames --log-dir ~/yam-eval/med-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/med-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()`
at the end of the episode. A box is in the bin when its centre is inside the bin's walls, below their tops.

| Outcome (`outcome()`) | Condition | Score |
|---|---|---|
| `unexpired_returned` | The in-date box (02/27) is in the bin | 0.0 |
| `2_of_2` | Both expired boxes (05/26, 09/25) in the bin, the in-date one not (all still) | 1.0 |
| `1_of_2` | One expired box in the bin, the in-date one not | 0.5 |
| `0_of_2` | No box in the bin | 0.0 |

Doing nothing scores 0, and so does putting all three in the bin. The date is given in the instruction so the task
doesn't depend on the model knowing today's date. In the real world, scoring is a look into the bin.

## The demo

The left arm puts the 05/26 box and then the 09/25 box in the bin, side by side, and leaves the 02/27 box. Each
grab pauses 2.5 s above the box first.

## Runtime and seeds

- Run limit: 2,400 steps (2 minutes at 20 Hz). The demo finishes in about 26 s of simulated time.
- Runtime per trial on an L40S: about 2.5 minutes for the scripted demo and about 8 minutes for a full
  2,400-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
