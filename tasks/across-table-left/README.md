# Put the cup on the coaster on the left of a person sitting across the table

Robots in homes and restaurants take requests phrased from the speaker's point of view. Here the speaker sits opposite
the robot, so 'my left' is the robot's right, a mix-up a robot that reads directions from its own point of view makes
every time.

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
  --instruction "i'm sitting across the table from you. put the cup on the coaster on my left" --scorer task_score \
  --max-steps 1200 --store-frames --log-dir ~/yam-eval/across-table-left-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "i'm sitting across the table from you. put the cup on the coaster on my left" --scorer task_score \
  --max-steps 1000 --store-frames --log-dir ~/yam-eval/across-table-left-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/across-table-left-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()` at the
end of the episode. The cup is on a coaster if its centre is within the coaster's 4.5 cm radius and it stands upright
(within about 25 degrees of vertical). The person faces the arms, so their left is the arms' right. 1.0: the cup
stands on the coaster 15 cm right of the midline (the person's left). 0.0 otherwise: on the middle coaster, on the
person's right, tipped over, or anywhere else.

| Outcome (`outcome()`) | Situation | Score |
|---|---|---|
| `persons_left` | On the coaster on the person's left (the arms' right), upright | 1.0 |
| `middle` | On the middle coaster | 0.0 |
| `persons_right` | On the coaster on the person's right (the arms' left) | 0.0 |
| `tipped` | On a coaster but tipped over | 0.0 |
| `none` | Anywhere else | 0.0 |

## The demo

The right arm picks up the cup, pausing 2.5 s above it first, and sets it down on the coaster on the arms' right,
which is the person's left.

## Runtime and seeds

- Run limit: 1,200 steps (1 minute at 20 Hz). The demo finishes in about 10 s of simulated time.
- Runtime per trial on an L40S: about 2.5 minutes for the scripted demo and about 5 minutes for a full
  1,200-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
