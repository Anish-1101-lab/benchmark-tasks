# Fill a lidded weekly pill organizer for Monday, Wednesday and Friday

A weekly pill organizer with seven compartments, each closed by its own hinged lid, is fixed to the table, with the
day letters M T W T F S S on a strip in front of it; three tablets lie on a small tray in front of the arms. The user
asks for one tablet in each of the Monday, Wednesday and Friday compartments, with their lids closed. The robot has to
read the day labels (two of the letters, T and S, appear twice), flip open the right lids by their tabs, place exactly
one tablet per requested day, and close each lid again, putting nothing in the other days.

| File | What it is |
|---|---|
| `task.py` | The task file: objects, `success()`, `score()`, `outcome()`, `distance()` and the scripted `demo()` |
| `lidkit.py` | Adds a fixed base with several lids on friction hinges to yam_arena task files (hooks `yam_arena.scene` and the embodiment's step and reset without modifying yam_arena). Adapted from `tasks/laptop-under-stack/hingekit.py` in this repository |

## Run a trial

On a Brev instance set up by the Robocurve launchable (Isaac Lab-Arena, the `yam_arena` embodiment, Dream-1),
from this folder (if your shell's start-up changes directory, pass the full path to `task.py`; `lidkit.py` must sit
next to it):

```bash
# Dream-1
inspect-robots run --embodiment yam_arena --policy dream \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "put one tablet in each of the monday, wednesday and friday compartments and close their lids" \
  --scorer task_score --max-steps 3600 --store-frames --log-dir ~/yam-eval/pill-dream

# Scripted demo
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "put one tablet in each of the monday, wednesday and friday compartments and close their lids" \
  --scorer task_score --max-steps 3000 --store-frames --log-dir ~/yam-eval/pill-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/pill-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end. Add `--epochs N` for repeated trials.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()`
at the end of the episode. A tablet is in a compartment when its centre is inside that compartment's walls, below
their tops. A lid is closed when it is open less than 10 degrees (its front edge less than 1.2 cm above the walls).

| Outcome (`outcome()`) | Condition | Score |
|---|---|---|
| `wrong_day` | Any tablet in Tuesday, Thursday, Saturday or Sunday | 0.0 |
| `<c>_closed_<o>_open` | `c` of Monday, Wednesday and Friday hold exactly one tablet with the lid closed, `o` with the lid left open | c/3 + o/6, rounded to two decimals |

So 3 closed is 1.0, 2 closed and 1 open 0.83, 3 open 0.5, and so on down to 0.0 when no requested day holds
exactly one tablet. A requested day with two or three tablets (a double dose) earns nothing for that day. Tablets
left on the tray, the table, the label strip, on top of a lid or on a wall top don't count. Opening other days' lids
isn't penalised. In the real world, scoring is a look at each lid's front edge, then a look into each compartment.

The lids are what stop this from being a plain pick-and-place: a compartment can't be filled without first finding
and lifting the right lid's tab, the lid has to be pushed past upright to stay out of the way, and the fill only
counts in full once the lid is closed again over the tablet.

## The demo

The arms take turns so they never reach into the middle together. For each day, one arm pinches the lid's tab and
lifts it along the hinge's arc to 50 degrees, lets go, and pushes the lid open past upright with closed fingers
(the stiff hinge then holds it leaning back). It picks a tablet off the tray, drops it into the compartment 1.5 cm
above the walls, then comes down 9 cm behind the hinge, pushes forward low against the open lid's outer face until
it is past upright, and follows its arc down, pressing it shut. The left arm does Monday and Wednesday and moves aside while the right arm waits at its ready pose;
then the right arm does Friday. The demo's waypoints add up to about 115 s; in Isaac Lab-Arena it reaches **1.0**
and ends on success after about 2,190 steps (110 s). Dream-1 scores 0.0: it never lifts a lid.

## Runtime and seeds

- Run limit: 3,600 steps (3 minutes at 20 Hz). Each of the three lids has to be opened and closed, so this is longer
  than a plain three-object pick-and-place needs.
- Runtime per trial on an L40S: about 8.5 minutes for the scripted demo (it reaches 1.0 and ends on success after
  about 2,190 steps) and about 11 minutes for a full 3,600-step Dream-1 run, including Isaac Sim start-up.
- Seeds: the layout is fixed (`-E object_jitter=0`), so every trial starts identically; no seed is needed.
  With jitter on, `--epochs N` uses the seeds 0..N-1.

## Third-party assets

None. Every object is built from box primitives in `task.py`. `lidkit.py` is adapted from code another team
contributed to this repository (`tasks/laptop-under-stack/hingekit.py`).
