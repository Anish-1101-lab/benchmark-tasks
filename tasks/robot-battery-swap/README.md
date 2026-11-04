# Swap a mobile robot's depleted battery for the charged one on the charger

A yellow robot chassis on the table has an open battery bay on top holding a depleted pack. Behind it, a charging
plate holds a charged pack that looks the same. The user asks for the swap: charged pack into the robot, depleted
pack onto the charger. The charger is occupied, so the order matters: the charged pack has to come off (or be held)
before the depleted one can go on. The bay leaves 8 mm around the pack, so it has to be lowered in straight.

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
  --instruction "swap the robot's depleted battery for the charged one on the charger, and leave the depleted one charging" \
  --scorer task_score --max-steps 2400 --store-frames --log-dir ~/yam-eval/batt-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "swap the robot's depleted battery for the charged one on the charger, and leave the depleted one charging" \
  --scorer task_score --max-steps 1200 --store-frames --log-dir ~/yam-eval/batt-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/batt-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()`
at the end of the episode.

| Outcome (`outcome()`) | Condition | Score |
|---|---|---|
| `swapped` | Charged pack in the robot and depleted pack on the charger | 1.0 |
| `robot_only` | Charged pack in the robot (centre within 1 cm of the bay's, bottom within 1 cm of its floor, still) | 0.5 |
| `dock_only` | Depleted pack on the charger (centre within 2.5 cm of the plate's, bottom within 1 cm of its top, still) | 0.5 |
| `neither` | Anything else, including doing nothing | 0.0 |

The packs start the other way round, so doing nothing scores 0. The robot's bay is the precise part (1 cm); the
charger is a flat contact plate, so 2.5 cm counts. In the real world, both are checked with a ruler, and the
packs' undersides are marked so the scorer knows which is which.

## The demo

A bimanual hand-off. The right arm lifts the charged pack off the plate and holds it up out of the way; the left
arm moves the depleted pack from the bay onto the plate and steps aside; then the right arm lowers the charged pack
into the bay. Both arms pause above each target before lowering.

In this simulator, the right arm's held pack hangs 2.2 cm right of the commanded point when it hovers above the
bay (measured), so the demo aims 2.2 cm left there. That correction is only in `demo()`; the scene and the scoring
use the true positions.

## Runtime and seeds

- Run limit: 2,400 steps (2 minutes at 20 Hz). The demo finishes in about 45 s of simulated time.
- Runtime per trial on an L40S: about 3 minutes for the scripted demo and about 8 minutes for a full
  2,400-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
