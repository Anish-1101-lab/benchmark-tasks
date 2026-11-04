# Sort parcels into chutes using a routing card

Three open chutes (bins) labelled A, B and C stand at the back of the table. Three small parcels, wrapped in red,
blue and green, wait in a line in front of the arms. A routing card on the right of the table gives each colour's
chute: red to C, blue to A, green to B. The robot has to read the card and apply it; the mapping is arbitrary on
purpose, so matching colours or guessing gets parcels missorted.

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
  --instruction "sort each parcel into the chute that the routing card lists for its colour" --scorer task_score \
  --max-steps 2400 --store-frames --log-dir ~/yam-eval/parcel-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "sort each parcel into the chute that the routing card lists for its colour" --scorer task_score \
  --max-steps 1200 --store-frames --log-dir ~/yam-eval/parcel-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/parcel-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()`
at the end of the episode. A parcel is in a chute when its centre is inside that bin's walls, below their tops.

| Outcome (`outcome()`) | Condition | Score |
|---|---|---|
| `missort` | Any parcel in a wrong chute | 0.0 |
| `3_of_3` | Red in C, blue in A and green in B (all still) | 1.0 |
| `2_of_3` | Two parcels in their own chutes, none in a wrong one | 0.67 |
| `1_of_3` | One parcel in its own chute, none in a wrong one | 0.33 |
| `0_of_3` | No parcel in any chute | 0.0 |

Doing nothing scores 0, and so does dropping every parcel into one chute (two of them are then missorted). Colour
matching gives nothing to go on: the parcels are red, blue and green, the chutes are grey. In the real world,
scoring is a look into each bin.

## The demo

The arms take turns so they never reach into the middle together: the left arm puts blue in A and green in B and
moves aside while the right arm waits at its ready pose, then the right arm puts red in C. Each grab pauses 2.5 s
above the parcel first.

## Runtime and seeds

- Run limit: 2,400 steps (2 minutes at 20 Hz). The demo finishes in about 40 s of simulated time.
- Runtime per trial on an L40S: about 3 minutes for the scripted demo and about 8 minutes for a full
  2,400-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
