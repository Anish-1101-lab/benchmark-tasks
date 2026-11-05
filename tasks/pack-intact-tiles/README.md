# Pack the intact tiles and leave the broken one

Packing by hand includes a quick visual check: a broken part must not ship. The three tiles here are identical except
that one is snapped in two, so the robot has to look before it packs.

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
  --instruction "pack the undamaged tiles in the box" --scorer task_score \
  --max-steps 2400 --store-frames --log-dir ~/yam-eval/pack-intact-tiles-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "pack the undamaged tiles in the box" --scorer task_score \
  --max-steps 1000 --store-frames --log-dir ~/yam-eval/pack-intact-tiles-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/pack-intact-tiles-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()` at the
end of the episode. A piece is in the box if its centre is inside the box's walls, below their tops. 1.0: both intact
tiles are in the box and neither half of the broken tile is. 0.0 otherwise: either half in the box, one intact tile
only, or none. There is no partial credit: a tile picked at random is intact two times in three, so a half score would
reward guessing.

| Outcome (`outcome()`) | Situation | Score |
|---|---|---|
| `2_of_2` | Both intact tiles in the box, no broken half | 1.0 |
| `1_of_2` | One intact tile, no broken half | 0.0 |
| `0_of_2` | Nothing in the box | 0.0 |
| `broken_packed` | Either half of the broken tile in the box | 0.0 |

## The demo

The arms take turns: the left arm packs the left intact tile and moves aside while the right arm waits at its ready
pose, then the right arm packs the middle one. Each grip pauses 2.5 s above the tile and closes across it at
mid-thickness; the tray lifts the tiles 3 cm so the fingers close clear of the table.

## Runtime and seeds

- Run limit: 2,400 steps (2 minutes at 20 Hz). The demo finishes in about 22 s of simulated time.
- Runtime per trial on an L40S: about 2.5 minutes for the scripted demo and about 8 minutes for a full
  2,400-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
