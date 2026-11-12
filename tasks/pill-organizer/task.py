"""On the station table: a weekly pill organizer (seven compartments in a row, each closed by its own snap lid with
its day letter, M T W T F S S, printed on it) and three caplets on a tray in front of the arms. The user asks for one
tablet in each of the Monday, Wednesday and Friday compartments, with their lids closed. The robot has to pop each of
those lids open by its tab, drop one caplet in, and press the lid until it snaps shut. Seeded resets move and turn
the organizer and move each caplet.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "put one tablet in each of the monday, wednesday and friday compartments and close their lids" \\
           --scorer task_score ...
"""

from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lidkit import Lidded  # noqa: E402
from yam_arena.constants import FINGER_CLOSED, FINGER_OPEN  # noqa: E402
from yam_arena.demo import Waypoint, pick_place_waypoints  # noqa: E402
from yam_arena.task_file import TABLE_TOP, Box  # noqa: E402

SCENE = "station"
TOP = TABLE_TOP[SCENE]

# -- the organizer ----------------------------------------------------------------------------------------------
# Seven compartments in a row along y, Monday on the left as seen from behind the arms (+y), Sunday on the right.
DAYS = ("M", "T", "W", "T", "F", "S", "S")
DAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
TARGETS = ("monday", "wednesday", "friday")
PITCH = 0.05  # compartment centre to centre (m)
WALL = 0.004  # wall thickness
INNER_D = 0.06  # compartment depth (x), inside the walls
WALL_H = 0.02  # wall height above the organizer's floor
BASE_T = 0.003  # floor plate thickness
X0 = 0.27  # the compartments' near inside edge (m forward)
FLOOR = TOP + BASE_T
WIDTH = len(DAYS) * PITCH + WALL
OUTER_D = INNER_D + 2 * WALL  # 6.8 cm, front of the front wall to back of the back wall
BLUE = (0.45, 0.62, 0.85)
LID_BLUE = (0.62, 0.76, 0.93)
BLACK = (0.05, 0.05, 0.05)

# Lids: a 2 mm plate over each compartment, hinged along the top of the back wall, with a grip tab sticking out
# 2.5 cm past the front wall. Lids are 4.8 cm wide (2 mm gaps between neighbours).
LID_T = 0.002
LID_W = PITCH - 0.002
TAB_OUT, TAB_W, TAB_H = 0.025, 0.016, 0.008  # the tab: reach past the front wall (x), width (y), height (z)
CLOSED_DEG = 3.0  # a lid counts as closed (snapped shut) below this angle: its front edge under 4 mm up
HOLD_TORQUE = 0.02  # N m: each hinge's friction (a 5 g lid's own weight makes at most 0.002 N m)
LATCH_DEG, LATCH_TORQUE = 4.0, 0.08  # the snap: below 4 deg a lid is pulled shut with 0.08 N m
YAW_JITTER_DEG = 15.0  # seeded resets also turn the organizer by up to this much (see lidkit)

BASE_POS = (X0 + INNER_D / 2, 0.0, TOP)  # the base frame's origin: the organizer's centre, on the table
HINGE_X = OUTER_D / 2  # in the base frame: the back wall's back face ...
HINGE_Z = BASE_T + WALL_H  # ... at the walls' top
HX, HZ = BASE_POS[0] + HINGE_X, TOP + HINGE_Z  # the hinge line in the world


def day_y(i: int) -> float:
    """The centre (y) of compartment i, 0 = Monday."""
    return (3 - i) * PITCH


BASE_BOXES = (
    ((0.0, 0.0, BASE_T / 2), (OUTER_D, WIDTH, BASE_T), BLUE),
    ((-INNER_D / 2 - WALL / 2, 0.0, BASE_T + WALL_H / 2), (WALL, WIDTH, WALL_H), BLUE),
    ((INNER_D / 2 + WALL / 2, 0.0, BASE_T + WALL_H / 2), (WALL, WIDTH, WALL_H), BLUE),
    *[
        ((0.0, day_y(0) + PITCH / 2 - k * PITCH, BASE_T + WALL_H / 2), (INNER_D, WALL, WALL_H), BLUE)
        for k in range(len(DAYS) + 1)
    ],
)
# The day letters are printed on the lids, as on real organizers: 5 x 7 block letters on 8 mm cells (4 cm wide,
# 5.6 cm tall, 8 mm strokes), raised 1 mm, tops toward the hinge so they read upright from behind the arms.
CELL = 0.008
GLYPHS = {
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
}
def _glyph_rects(rows):
    """A glyph's ink as rectangles (row, col, rows tall, cols wide), stacking identical runs in consecutive rows."""
    runs = []
    for r, row in enumerate(rows):
        c = 0
        while c < len(row):
            if row[c] == "#":
                start = c
                while c < len(row) and row[c] == "#":
                    c += 1
                runs.append([r, start, 1, c - start])
            else:
                c += 1
    merged = []
    for run in runs:
        below = next((m for m in merged if m[1] == run[1] and m[3] == run[3] and m[0] + m[2] == run[0]), None)
        if below:
            below[2] += 1
        else:
            merged.append(run)
    return merged


def letter_boxes(ch: str):
    """A day letter's ink as boxes in the lid frame, centred on the closed lid's plate."""
    top_x = -OUTER_D / 2 + 7 * CELL / 2  # the letter's top edge (toward the hinge, +x)
    left_y = 5 * CELL / 2  # the letter's left edge (+y)
    return tuple(
        ((top_x - (r + h / 2) * CELL, left_y - (c + w / 2) * CELL, LID_T + 0.0005), (h * CELL, w * CELL, 0.001), BLACK)
        for r, c, h, w in _glyph_rects(GLYPHS[ch])
    )


LID_PLATE = (  # in the lid frame: origin on the hinge, the lid reaching out along -x when closed
    ((-OUTER_D / 2, 0.0, LID_T / 2), (OUTER_D, LID_W, LID_T), LID_BLUE),
    ((-OUTER_D - TAB_OUT / 2, 0.0, 0.0), (TAB_OUT, TAB_W, TAB_H), LID_BLUE),
)
ORGANIZER = Lidded(
    "organizer",
    pos=BASE_POS,
    size=(OUTER_D, WIDTH, HINGE_Z),
    color=BLUE,
    mass=1.5,  # a free body standing in for the real organizer stuck down with putty; seeded resets move it
    base_boxes=BASE_BOXES,
    lids=tuple(((HINGE_X, day_y(i), HINGE_Z), LID_PLATE + letter_boxes(ch)) for i, ch in enumerate(DAYS)),
    lid_mass=0.005,
    hold_torque=HOLD_TORQUE,
    upper_deg=150.0,
    latch_deg=LATCH_DEG,
    latch_torque=LATCH_TORQUE,
    yaw_jitter_deg=YAW_JITTER_DEG,
    friction=0.6,
)

# -- the tablets ------------------------------------------------------------------------------------------------
# Three identical white caplets, 22 x 10 x 8 mm and 2 g, lying flat on a pill tray, long side pointing forward.
# The tray is a fixed grey block, 3 cm tall, so a gripper can close on a caplet without its fingertips meeting the
# table. Seeded resets (-E object_jitter=0.03) move each caplet up to 3 cm each way; their nominal spots are 8 cm
# apart, so they never overlap, and the tray is big enough that they stay on it.
TRAY_H = 0.03
TRAY = Box("pill_tray", pos=(0.13, 0.0, TOP + TRAY_H / 2), size=(0.10, 0.26, TRAY_H), color=(0.55, 0.57, 0.6))
TABLET_SIZE = (0.022, 0.010, 0.008)
TABLET_XY = ((0.13, 0.08), (0.13, 0.0), (0.13, -0.08))
TABLETS = [
    Box(f"tablet_{k}", pos=(x, y, TOP + TRAY_H + TABLET_SIZE[2] / 2), size=TABLET_SIZE, color=(0.96, 0.96, 0.92),
        mass=0.002)
    for k, (x, y) in enumerate(TABLET_XY)
]

OBJECTS = [ORGANIZER, TRAY, *TABLETS]

# -- scoring ----------------------------------------------------------------------------------------------------


ON_FLOOR = FLOOR + 0.013  # a caplet resting on a compartment's floor (flat, on its side or on end) has its centre below this


def in_organizer(organizer, point) -> tuple[float, float, float]:
    """A world point in the organizer's base frame (origin at its centre on the table; it may have been moved and
    turned about the vertical)."""
    x, y, z, w = (float(v) for v in organizer.quat_xyzw)
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    dx, dy, dz = (float(p) - float(o) for p, o in zip(point, organizer.pos))
    c, s = math.cos(yaw), math.sin(yaw)
    return (c * dx + s * dy, -s * dx + c * dy, dz)


def compartment(organizer, state):
    """The day whose compartment holds this tablet, or None. It must have been let go (no gripper closed on it): its
    centre inside the walls, within 13 mm of the compartment's floor (lying on it, not held above it), and still."""
    x, y, z = in_organizer(organizer, state.pos)
    if getattr(state, "held", False) or not (abs(x) < INNER_D / 2 and z < ON_FLOOR - TOP and state.resting()):
        return None
    for i, name in enumerate(DAY_NAMES):
        if abs(y - day_y(i)) < (PITCH - WALL) / 2:
            return name
    return None


def counts(objects) -> dict[str, int]:
    """Tablets per compartment."""
    out = {name: 0 for name in DAY_NAMES}
    for k in range(len(TABLETS)):
        day = compartment(objects["organizer"], objects[f"tablet_{k}"])
        if day:
            out[day] += 1
    return out


def lid_closed(objects, day: str) -> bool:
    """The day's lid is snapped shut: its hinge is open less than CLOSED_DEG."""
    return math.degrees(objects["organizer"].angles[DAY_NAMES.index(day)]) < CLOSED_DEG


def tally(objects) -> tuple[int, int] | None:
    """None if any tablet is in a day that wasn't asked for. Otherwise (closed, open): how many of Monday,
    Wednesday and Friday hold exactly one tablet with their lid closed, and with their lid left open."""
    c = counts(objects)
    if any(n for day, n in c.items() if day not in TARGETS):
        return None
    good = [d for d in TARGETS if c[d] == 1]
    closed = sum(lid_closed(objects, d) for d in good)
    return closed, len(good) - closed


def outcome(objects) -> str:
    """'wrong_day', or '<closed>_closed_<open>_open' for the requested days holding exactly one tablet."""
    t = tally(objects)
    return "wrong_day" if t is None else f"{t[0]}_closed_{t[1]}_open"


def score(objects):
    """0 if any tablet is in a day that wasn't asked for. Otherwise, for each of Monday, Wednesday and Friday that
    holds exactly one tablet: 1/3 if its lid is closed, 1/6 if it was left open. A double dose earns nothing for
    that day. Rounded to two decimals."""
    t = tally(objects)
    return 0.0 if t is None else round(t[0] / 3 + t[1] / 6, 2)


def success(objects):
    """Exactly one tablet lying in each of Monday, Wednesday and Friday, their lids snapped shut, none elsewhere."""
    return score(objects) == 1.0


def distance(objects):
    """Per requested day: 1 while it lacks its single tablet, 0.5 while it has it but the lid is open."""
    c = counts(objects)
    return float(sum(1.0 if c[d] != 1 else (0.0 if lid_closed(objects, d) else 0.5) for d in TARGETS))


# -- scripted demo (yam_scripted plays it open loop; run with -E object_jitter=0) --------------------------------
TRAVEL = TOP + 0.12
TIP_BELOW_TCP = 0.0128  # the closed fingertips' lowest point below the TCP
PINCH_LOCAL = (-OUTER_D - TAB_OUT + 0.010, 0.0, 0.0)  # 1 cm in from the tab's tip: pads 1.5 cm clear of the wall
LIFT_TO_DEG = 50
PUSH_YAW = math.pi / 2  # closed fingers, housing's narrow side across y
PUSH_Z = HZ + 0.045  # the straight push that swings a half-open lid past upright
CLOSE_BACK, CLOSE_Z = 0.09, 0.03  # where the closing push starts: behind the hinge, above the hinge line
PRESS_LOCAL = (-0.05, 0.0, LID_T + TIP_BELOW_TCP - 0.003)  # closed tips 3 mm into the lid's top, 5 cm from the hinge


def lid_point(local, deg: float, y: float) -> tuple[float, float, float]:
    """A point given in a lid's frame, in the world, with that lid (centred at ``y``) open ``deg`` degrees."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    x, _, z = local
    return (float(HX + c * x + s * z), float(y), float(HZ - s * x + c * z))


def _fill(tablet: int, day: str) -> list[Waypoint]:
    """Open the day's lid, put the tablet in, close the lid. One arm."""
    y = day_y(DAY_NAMES.index(day))
    w: list[Waypoint] = []
    # 1. Pinch the tab and lift the lid to 50 deg along the hinge's arc; let go.
    px, py, pz = lid_point(PINCH_LOCAL, 0, y)
    w += [
        Waypoint(1.5, (px, py, TRAVEL), FINGER_OPEN, f"over {day}'s tab"),
        Waypoint(1.5, (px, py, pz), FINGER_OPEN, "fingers either side of the tab"),
        Waypoint(0.8, (px, py, pz), FINGER_CLOSED, "pinch the tab"),
    ]
    w += [Waypoint(0.4, lid_point(PINCH_LOCAL, d, y), FINGER_CLOSED, f"lift the lid to {d} deg")
          for d in range(5, LIFT_TO_DEG + 1, 5)]
    ex, ey, ez = lid_point(PINCH_LOCAL, LIFT_TO_DEG, y)
    w += [
        Waypoint(0.3, (ex, ey, ez), FINGER_CLOSED, "hold"),
        Waypoint(0.6, (ex, ey, ez), FINGER_OPEN, "let go of the tab"),
        Waypoint(0.8, (HX - 0.10, ey, ez), FINGER_OPEN, "back off, in front of the tab"),
        # 2. Closed fingers under the raised lid's edge, then straight back over the hinge: the lid swings past
        #    upright and its friction hinge holds it open, leaning back.
        Waypoint(0.8, (HX - 0.10, y, PUSH_Z), FINGER_CLOSED, "under the lid's edge", PUSH_YAW),
        Waypoint(3.0, (HX + 0.015, y, PUSH_Z), FINGER_CLOSED, "push the lid open past upright", PUSH_YAW),
        Waypoint(0.5, (HX + 0.015, y, PUSH_Z), FINGER_CLOSED, "hold", PUSH_YAW),
        Waypoint(1.0, (HX - 0.06, y, TRAVEL), FINGER_OPEN, "up and away", 0.0),
    ]
    # 3. The tablet from the tray into the compartment, let go 1.5 cm above the walls.
    place = (X0 + INNER_D / 2, y, FLOOR + WALL_H + 0.015)
    grip_z = TOP + TRAY_H + TABLET_SIZE[2] / 2
    plan = pick_place_waypoints((*TABLET_XY[tablet], grip_z), place, travel_z=TRAVEL)
    hover = plan[0]  # settle above the caplet before descending, as the station's own demo does
    w += [hover, Waypoint(2.5, hover.pos, FINGER_OPEN, "wait", hover.yaw), *plan[1:]]
    # 4. Closed fingers come down well behind the open lid's tab (it leans back as far as 140 deg), push forward low
    #    against its outer face until it is past upright, then follow its arc down and press it shut.
    w += [
        Waypoint(1.5, (HX + CLOSE_BACK, y, TRAVEL), FINGER_CLOSED, "behind the open lid", PUSH_YAW),
        Waypoint(1.0, (HX + CLOSE_BACK, y, HZ + CLOSE_Z), FINGER_CLOSED, "down behind it", PUSH_YAW),
        Waypoint(2.0, (HX - 0.01, y, HZ + CLOSE_Z), FINGER_CLOSED, "push it forward past upright", PUSH_YAW),
    ]
    w += [Waypoint(0.25, lid_point(PRESS_LOCAL, d, y), FINGER_CLOSED, f"lid down to {d} deg", PUSH_YAW)
          for d in range(65, -1, -5)]
    w += [
        Waypoint(0.5, lid_point(PRESS_LOCAL, -2, y), FINGER_CLOSED, "press it until it snaps shut", PUSH_YAW),
        Waypoint(1.0, (X0, y, TRAVEL), FINGER_OPEN, "up", 0.0),
    ]
    return w


def demo():
    """The arms take turns, so they never reach into the middle together: the left arm fills Monday (tablet 0) and
    Wednesday (tablet 1) and moves aside, while the right arm waits at its ready pose; then the right arm fills
    Friday (tablet 2). Filling a day: pinch the lid's tab and lift it to 50 deg, push it open past upright with
    closed fingers, put the tablet in, push the lid back over from behind and press it shut."""
    left = _fill(0, "monday") + _fill(1, "wednesday")
    left.append(Waypoint(1.5, (0.18, 0.25, TRAVEL), FINGER_OPEN, "out of the way", 0.0))
    left_time = sum(w.duration for w in left)
    right_ready = (0.318, -0.298, TOP + 0.257)  # the right arm's ready pose (its TCP)
    right = [Waypoint(left_time, right_ready, FINGER_OPEN, "wait for the left arm", 0.0), *_fill(2, "friday")]
    right.append(Waypoint(1.5, (0.18, -0.25, TRAVEL), FINGER_OPEN, "out of the way", 0.0))
    return {"left": left, "right": right}
