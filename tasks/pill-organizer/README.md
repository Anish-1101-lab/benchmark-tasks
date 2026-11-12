# Fill a lidded weekly pill organizer for Monday, Wednesday and Friday

A weekly pill organizer with seven compartments, each closed by its own snap lid with its day letter (M T W T F S S)
printed on it, is stuck to the table; three caplets lie on a tray in front of the arms. Every trial the organizer is
moved and turned, and each caplet moved, by its own random amount. The user asks for one tablet in each of the
Monday, Wednesday and Friday compartments, with their lids closed. The robot has to pop the right lids open by their small tabs, keep each lid out
of the way while it drops one caplet into the 4.6 cm cell, and press the lid down until it snaps shut again, putting
nothing in the other days.

| File | What it is |
|---|---|
| `task.py` | The task file: objects, `success()`, `score()`, `outcome()`, `distance()` and the scripted `demo()` |
| `lidkit.py` | Adds a base with several snap lids on friction hinges to yam_arena task files (hooks `yam_arena.scene` and the embodiment's step and reset without modifying yam_arena). Adapted from `tasks/laptop-under-stack/hingekit.py` in this repository |

## Run a trial

On a Brev instance set up by the Robocurve launchable (Isaac Lab-Arena, the `yam_arena` embodiment, Dream-1),
from this folder (if your shell's start-up changes directory, pass the full path to `task.py`; `lidkit.py` must sit
next to it):

```bash
# Dream-1: a randomized start; --epochs N runs seeds 0..N-1
inspect-robots run --embodiment yam_arena --policy dream \
  -E task=task.py -E object_jitter=0.03 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "put one tablet in each of the monday, wednesday and friday compartments and close their lids" \
  --scorer task_score --max-steps 3600 --epochs 1 --store-frames --log-dir ~/yam-eval/pill-dream

# Scripted demo: open loop, so it runs on the nominal layout
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=task.py -E object_jitter=0 -E control_hz=20 -E cam_width=320 -E cam_height=176 \
  --instruction "put one tablet in each of the monday, wednesday and friday compartments and close their lids" \
  --scorer task_score --max-steps 3000 --store-frames --log-dir ~/yam-eval/pill-demo

# Videos (one MP4 per camera)
for log in ~/yam-eval/pill-*/*.json; do inspect-robots video "$log"; done
```

The run prints `task_score` at the end.

## Scoring

`--scorer task_score` gives 1.0 when `success()` holds for 1 s (the episode then ends), and otherwise `score()`
at the end of the episode.

- A tablet is **in** a compartment only once it has been let go and lies on that compartment's floor: its centre
  inside the walls, less than 13 mm above the floor (a caplet lying flat, on its side or on end), not moving, and no
  gripper closed on it (`lidkit.py` flags a free object as held when a gripper's pads are 0.5-15 mm apart within
  15 mm of it). A caplet still in a gripper, or resting on a wall top or a lid, is in no compartment.
- A lid is **closed** only when it is snapped shut: open less than 3 degrees, so its front edge is less than 4 mm
  above the wall tops.

| Outcome (`outcome()`) | Condition | Score |
|---|---|---|
| `wrong_day` | Any tablet in Tuesday, Thursday, Saturday or Sunday | 0.0 |
| `<c>_closed_<o>_open` | `c` of Monday, Wednesday and Friday hold exactly one tablet with the lid closed, `o` with the lid not closed | c/3 + o/6, rounded to two decimals |

So 3 closed is 1.0, 2 closed and 1 open 0.83, 3 open 0.5, and so on down to 0.0 when no requested day holds
exactly one tablet. A requested day with two or three tablets (a double dose) earns nothing for that day. Opening
other days' lids isn't penalised. In the real world, scoring is a ruler at each requested lid's front edge, then a
look into each compartment.

What makes this physical rather than a reading exercise: a compartment can't be filled without releasing a snap by
lifting a 1.6 cm tab with about 1 N, the lid has to be pushed past upright to stay out of the way, the caplet has
to go into a 4.6 x 6 cm cell past the raised lid, and full credit needs the lid pressed until it snaps shut over the
tablet. The organizer is moved and turned and the caplets are moved every trial, so a fixed motion can't simply be
replayed.

## The demo

The arms take turns so they never reach into the middle together. For each day, one arm pinches the lid's tab and
lifts it along the hinge's arc to 50 degrees (releasing the snap), lets go, and pushes the lid open past upright with
closed fingers (the stiff hinge then holds it leaning back). It picks a caplet off the tray, drops it into the
compartment 1.5 cm above the walls, then comes down 9 cm behind the hinge, pushes forward low against the open lid's
outer face until it is past upright, and follows its arc down, pressing it until it snaps shut. The left arm does
Monday and Wednesday and moves aside while the right arm waits at its ready pose; then the right arm does Friday.

The demo is open loop: it uses only the layout given in the setup (nominal caplet spots, `-E object_jitter=0`), no
simulator state. In Isaac Lab-Arena it reaches **1.0** and ends on success after about 2,190 steps (110 s).
Dream-1 scores 0.0: it never lifts a lid.

## Runtime and seeds

- Run limit: 3,600 steps (3 minutes at 20 Hz). Each of the three lids has to be opened and closed, so this is longer
  than a plain three-object pick-and-place needs.
- Runtime per trial on an L40S: about 8.5 minutes for the scripted demo and about 11 minutes for a full 3,600-step
  Dream-1 run, including Isaac Sim start-up.
- Seeds: with `-E object_jitter=0.03`, `--epochs N` runs seeds 0..N-1; each seed moves the organizer and each caplet
  by its own offset of up to 3 cm forward/back and left/right; from the organizer's offset, `lidkit.py` also draws a
  turn of up to 15 degrees for it. The tray never moves. (In the sim the organizer is a free 1.5 kg body, standing in
  for the real one stuck down with putty, so the reset can move it.) With `-E object_jitter=0` the layout is nominal.
- Real-world trials: before each trial, roll a six-sided die twice for the organizer and twice per caplet, once for
  forward/back and once for left/right, and shift it from its marked spot by 1 = -3 cm, 2 = -2 cm, 3 = -1 cm,
  4 = +1 cm, 5 = +2 cm, 6 = +3 cm; roll once more for the organizer's turn about its centre: 1 = -15, 2 = -9,
  3 = -3, 4 = +3, 5 = +9, 6 = +15 degrees, counterclockwise seen from above.

## Third-party assets

None. Every object is built from box primitives in `task.py`. `lidkit.py` is adapted from code another team
contributed to this repository (`tasks/laptop-under-stack/hingekit.py`).
