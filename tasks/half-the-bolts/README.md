# Put half of the six bolts in a cup

Counting out parts ('half of these', 'three of those') is routine in assembly and stores work, and counting is a known
weak spot of vision-language-action models, which tend to move everything or a single item. The robot has to count the
bolts and halve the number.

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
  --instruction "put half of the bolts in the cup" --scorer task_score \
  --max-steps 2400 --store-frames --log-dir ~/yam-eval/half-the-bolts-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "put half of the bolts in the cup" --scorer task_score \
  --max-steps 1000 --store-frames --log-dir ~/yam-eval/half-the-bolts-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/half-the-bolts-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()` at the
end of the episode. A bolt is in the cup if its centre is inside the cup's walls, below their tops. 1.0: exactly three
bolts are in the cup, any three. 0.0 otherwise: fewer, more, or none.

| Outcome (`outcome()`) | Situation | Score |
|---|---|---|
| `3_in_cup` | Exactly three bolts in the cup | 1.0 |
| `0_in_cup .. 6_in_cup (not 3)` | Any other number | 0.0 |

## The demo

The arms take turns: the left arm puts the two leftmost bolts in the cup and moves aside while the right arm waits at
its ready pose, then the right arm puts the rightmost bolt in. Each grip pauses 2.5 s above the bolt and closes 4 cm
above the table.

## Runtime and seeds

- Run limit: 2,400 steps (2 minutes at 20 Hz). The demo finishes in about 36 s of simulated time.
- Runtime per trial on an L40S: about 2.5 minutes for the scripted demo and about 8 minutes for a full
  2,400-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
