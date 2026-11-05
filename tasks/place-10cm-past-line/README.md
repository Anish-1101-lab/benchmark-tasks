# Set a block down 10 cm beyond a taped line, measuring with a ruler

Layout work, from setting out fixtures to spacing parts on a bench, means placing things a measured distance from a
reference line. A robot that places things 'about there' fails it; here it can use the ruler on the table.

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
  --instruction "put the block down with its centre 10 cm beyond the red line" --scorer task_score \
  --max-steps 1200 --store-frames --log-dir ~/yam-eval/place-10cm-past-line-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "put the block down with its centre 10 cm beyond the red line" --scorer task_score \
  --max-steps 1000 --store-frames --log-dir ~/yam-eval/place-10cm-past-line-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/place-10cm-past-line-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()` at the
end of the episode. The error is how far the block's centre is from 10 cm beyond the tape's centre line, measured
square to the tape; its sideways position doesn't matter. The block must rest on the table (its centre no more than
2.8 cm above it; on the ruler counts). 1.0: error 1 cm or less. 0.5: error 2 cm or less. 0.0: a larger error, or not
resting on the table.

| Outcome (`outcome()`) | Situation | Score |
|---|---|---|
| `within_1cm` | Centre within 1 cm of 10 cm beyond the line | 1.0 |
| `within_2cm` | Within 2 cm | 0.5 |
| `off` | Further off, on the table | 0.0 |
| `not_on_table` | Held up or fallen off | 0.0 |

## The demo

The right arm picks up the block, pausing 2.5 s above it first, and sets it down 10 cm beyond the line, in line with
where it started.

## Runtime and seeds

- Run limit: 1,200 steps (1 minute at 20 Hz). The demo finishes in about 10 s of simulated time.
- Runtime per trial on an L40S: about 2.5 minutes for the scripted demo and about 5 minutes for a full
  1,200-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.
