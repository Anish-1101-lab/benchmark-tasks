"""On the station table: five metal spacers lying side by side on a parts tray, 10, 8, 6, 12 and 8 cm long, with
their near ends lined up at the zero of a printed centimetre ruler; and an open kit cup behind the tray. For a robot
joint's build kit, the user asks for both 8 cm spacers. The spacers differ only in length, so the robot has to
measure them against the ruler. The tray, ruler and cup are fixed; the spacers are loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "put the two 8 cm spacers in the kit cup" --scorer task_score ...
"""

from yam_arena.demo import FINGER_OPEN, Waypoint, pick_place_waypoints
from yam_arena.task_file import TABLE_TOP, Box

SCENE = "station"
TOP = TABLE_TOP[SCENE]
WHITE = (0.95, 0.95, 0.95)
BLACK = (0.05, 0.05, 0.05)

# -- parts tray -------------------------------------------------------------------------------------------------
TRAY_H = 0.03  # a fixed block the spacers lie on, so the fingers can close around them clear of the table
TRAY = Box("parts_tray", pos=(0.17, 0.02, TOP + TRAY_H / 2), size=(0.22, 0.46, TRAY_H), color=(0.30, 0.32, 0.36))
TRAY_TOP = TOP + TRAY_H

# -- spacers ----------------------------------------------------------------------------------------------------
SECTION = 0.02  # square cross-section, 2 x 2 cm
NEAR_END = 0.10  # every spacer's near end (m forward), at the ruler's zero
SPACERS = {  # name: (y, length)
    "s1": (0.16, 0.10),
    "s2": (0.08, 0.08),
    "s3": (0.00, 0.06),
    "s4": (-0.08, 0.12),
    "s5": (-0.16, 0.08),
}
TARGET = {n for n, (_, length) in SPACERS.items() if abs(length - 0.08) < 1e-9}
assert TARGET == {"s2", "s5"}
STEEL = (0.72, 0.74, 0.77)
SPACER_BOXES = [
    Box(f"spacer_{n}", pos=(NEAR_END + length / 2, y, TRAY_TOP + SECTION / 2), size=(length, SECTION, SECTION),
        color=STEEL, mass=0.03)
    for n, (y, length) in SPACERS.items()
]

# -- ruler ------------------------------------------------------------------------------------------------------
# A white strip on the tray along the spacers' length, left of the leftmost spacer: 0 to 14 cm, a 1 cm black tick
# every centimetre and a 2 cm tick every 5 cm, all ticks starting at the strip's right edge.
RULER_Y, RULER_W = 0.215, 0.03
RULER = [Box("ruler", pos=(NEAR_END + 0.07, RULER_Y, TRAY_TOP + 0.0015), size=(0.15, RULER_W, 0.003), color=WHITE)]
for cm in range(0, 15):
    tick = 0.02 if cm % 5 == 0 else 0.01
    RULER.append(Box(f"ruler_tick_{cm}", pos=(NEAR_END + cm / 100, RULER_Y - RULER_W / 2 + tick / 2, TRAY_TOP + 0.0035),
                     size=(0.0015, tick, 0.001), color=BLACK))

# -- kit cup ----------------------------------------------------------------------------------------------------
CUP_XY = (0.38, 0.0)
CUP_IN = 0.13
WALL, WALL_H, BASE_T = 0.004, 0.05, 0.003
FLOOR = TOP + BASE_T
BLUE = (0.18, 0.36, 0.72)


def _cup() -> list[Box]:
    (cx, cy), h, out = CUP_XY, FLOOR + WALL_H / 2, CUP_IN + 2 * WALL
    return [
        Box("cup_floor", pos=(cx, cy, TOP + BASE_T / 2), size=(out, out, BASE_T), color=BLUE),
        Box("cup_front", pos=(cx - CUP_IN / 2 - WALL / 2, cy, h), size=(WALL, out, WALL_H), color=BLUE),
        Box("cup_back", pos=(cx + CUP_IN / 2 + WALL / 2, cy, h), size=(WALL, out, WALL_H), color=BLUE),
        Box("cup_left", pos=(cx, cy + CUP_IN / 2 + WALL / 2, h), size=(CUP_IN, WALL, WALL_H), color=BLUE),
        Box("cup_right", pos=(cx, cy - CUP_IN / 2 - WALL / 2, h), size=(CUP_IN, WALL, WALL_H), color=BLUE),
    ]


OBJECTS = [TRAY, *SPACER_BOXES, *RULER, *_cup()]

# -- scoring ----------------------------------------------------------------------------------------------------


def in_cup(state) -> bool:
    """The spacer's centre is inside the cup's walls, below their tops."""
    x, y, z = (float(v) for v in state.pos)
    return abs(x - CUP_XY[0]) < CUP_IN / 2 and abs(y - CUP_XY[1]) < CUP_IN / 2 and z < FLOOR + WALL_H


def kit(objects) -> set[str]:
    return {n for n in SPACERS if in_cup(objects[f"spacer_{n}"])}


def outcome(objects) -> str:
    """'exact' (both 8 cm spacers, nothing else), 'one' (one of them, nothing else), 'empty', or 'wrong'."""
    k = kit(objects)
    if k == TARGET:
        return "exact"
    if not k:
        return "empty"
    return "one" if k < TARGET else "wrong"


def success(objects):
    """The cup holds exactly the two 8 cm spacers, both still."""
    return outcome(objects) == "exact" and all(objects[f"spacer_{n}"].resting() for n in TARGET)


def distance(objects):
    """8 cm spacers not yet in the cup, plus any other spacer in it."""
    k = kit(objects)
    return float(len(TARGET - k) + len(k - TARGET))


def score(objects):
    """1.0 if the cup holds exactly the two 8 cm spacers; 0 otherwise. No partial credit: a spacer picked at random
    is 8 cm long two times in five, so a half score would reward guessing."""
    return 1.0 if outcome(objects) == "exact" else 0.0


def demo():
    """The arms take turns: the left arm puts spacer s2 (8 cm, second from the left) in the cup and moves aside while
    the right arm waits at its ready pose; then the right arm puts spacer s5 (8 cm, rightmost) in. Each grip pauses
    2.5 s above the spacer, closes across its 2 cm width at its middle, and lets go 1.5 cm above the cup walls."""
    travel_z = TOP + 0.16
    grip_z = TRAY_TOP + SECTION / 2
    drop_z = FLOOR + WALL_H + 0.015 + SECTION / 2

    def into(name: str, dy: float):
        y, length = SPACERS[name]
        plan = pick_place_waypoints((NEAR_END + length / 2, y, grip_z), (CUP_XY[0], CUP_XY[1] + dy, drop_z),
                                    travel_z=travel_z)
        hover = plan[0]
        return [hover, Waypoint(2.5, hover.pos, FINGER_OPEN, "wait", hover.yaw), *plan[1:]]

    left = into("s2", 0.03) + [Waypoint(1.5, (0.18, 0.30, travel_z), FINGER_OPEN, "out of the way", 0.0)]
    left_time = sum(w.duration for w in left)
    right_ready = (0.318, -0.298, TOP + 0.257)
    right = [Waypoint(left_time, right_ready, FINGER_OPEN, "wait for the left arm", 0.0), *into("s5", -0.03)]
    right.append(Waypoint(1.5, (0.10, -0.28, travel_z), FINGER_OPEN, "out of the way", 0.0))
    return {"left": left, "right": right}
