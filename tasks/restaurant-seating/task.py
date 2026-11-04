"""On the station table: a model restaurant floor with four square tables, each with a different number of chairs
(2, 3, 4 and 5), and two reservation markers (red and blue) in front of the arms. The host's instruction: the red
party needs the table with 4 chairs, the blue party the table with 2 chairs. The robot has to count the chairs at
each table. The tables and chairs are fixed; the markers are loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "seat the parties: put the red marker on the table with 4 chairs and the blue marker on the
           table with 2 chairs" --scorer task_score ...
"""

from yam_arena.demo import FINGER_OPEN, Waypoint, pick_place_waypoints
from yam_arena.task_file import TABLE_TOP, Box

SCENE = "station"
TOP = TABLE_TOP[SCENE]

# -- tables and chairs ------------------------------------------------------------------------------------------
TABLE = (0.12, 0.12, 0.03)  # top size x, y and height (m)
TABLE_TOP_Z = TOP + TABLE[2]
CHAIR = (0.03, 0.03, 0.04)
GAP = 0.01  # between a table's edge and its chairs
WOOD = (0.55, 0.38, 0.22)
CHAIR_GREY = (0.45, 0.47, 0.5)

# Sides: "far" (+x), "near" (-x), "left" (+y), "right" (-y). A side with two chairs gets them 3 cm either side of
# its middle. Facing sides between tables are kept empty so chairs never touch.
TABLES = {
    "far_left": ((0.40, 0.13), {"far": 1, "left": 1}),  # 2 chairs
    "far_right": ((0.40, -0.13), {"far": 1, "left": 1, "right": 1}),  # 3 chairs
    "near_left": ((0.20, 0.13), {"near": 2, "left": 2, "right": 1}),  # 5 chairs
    "near_right": ((0.20, -0.13), {"near": 2, "left": 1, "right": 1}),  # 4 chairs
}
TARGET = {"red": "near_right", "blue": "far_left"}  # the tables with 4 and 2 chairs


def n_chairs(name: str) -> int:
    return sum(TABLES[name][1].values())


assert n_chairs(TARGET["red"]) == 4 and n_chairs(TARGET["blue"]) == 2
assert sorted(n_chairs(t) for t in TABLES) == [2, 3, 4, 5]


def _chairs(name: str) -> list[Box]:
    (tx, ty), sides = TABLES[name]
    off = TABLE[0] / 2 + GAP + CHAIR[0] / 2
    out = []
    for side, n in sides.items():
        dx, dy = {"far": (off, 0), "near": (-off, 0), "left": (0, off), "right": (0, -off)}[side]
        along = [0.0] if n == 1 else [-0.03, 0.03]
        for k, a in enumerate(along):
            x, y = (tx + dx, ty + a) if side in ("far", "near") else (tx + a, ty + dy)
            out.append(Box(f"chair_{name}_{side}_{k}", pos=(x, y, TOP + CHAIR[2] / 2), size=CHAIR, color=CHAIR_GREY))
    return out


FURNITURE = []
for name, ((tx, ty), _) in TABLES.items():
    FURNITURE.append(Box(f"table_{name}", pos=(tx, ty, TOP + TABLE[2] / 2), size=TABLE, color=WOOD))
    FURNITURE += _chairs(name)

# -- reservation markers ----------------------------------------------------------------------------------------
MARKER = 0.05
MARKERS = {"red": ((0.07, -0.06), (0.80, 0.12, 0.12)), "blue": ((0.07, 0.06), (0.15, 0.32, 0.80))}
MARKER_BOXES = [
    Box(f"marker_{c}", pos=(*xy, TOP + MARKER / 2), size=(MARKER, MARKER, MARKER), color=col, mass=0.05)
    for c, (xy, col) in MARKERS.items()
]

OBJECTS = [*FURNITURE, *MARKER_BOXES]

# -- scoring ----------------------------------------------------------------------------------------------------


def table_of(state):
    """The table a marker rests on (its centre over the table top, its bottom on the top), or None."""
    x, y = (float(v) for v in state.pos[:2])
    bottom = float(state.low[2])
    for name, ((tx, ty), _) in TABLES.items():
        if abs(x - tx) < TABLE[0] / 2 and abs(y - ty) < TABLE[1] / 2 and abs(bottom - TABLE_TOP_Z) < 0.01:
            return name
    return None


def outcome(objects) -> str:
    """'seated' (both right), 'red_only', 'blue_only', or 'neither'."""
    ok = {c: table_of(objects[f"marker_{c}"]) == TARGET[c] for c in MARKERS}
    return {(True, True): "seated", (True, False): "red_only", (False, True): "blue_only"}.get(
        (ok["red"], ok["blue"]), "neither")


def success(objects):
    """Red on the 4-chair table and blue on the 2-chair table, both still."""
    return outcome(objects) == "seated" and all(objects[f"marker_{c}"].resting() for c in MARKERS)


def distance(objects):
    """Markers not yet on their table (0 to 2)."""
    return float(sum(table_of(objects[f"marker_{c}"]) != TARGET[c] for c in MARKERS))


def score(objects):
    """1.0 if both markers are on their tables; 0 otherwise. No partial credit: a marker put on a random table would
    be right one time in four, so a half score would reward guessing."""
    return 1.0 if outcome(objects) == "seated" else 0.0


def demo():
    """The arms take turns: the left arm puts the blue marker on the 2-chair table (far left) and moves aside while
    the right arm waits at its ready pose; then the right arm puts the red marker on the 4-chair table (near
    right). Each grip pauses 2.5 s above the marker and lets go 1 cm above the table top."""
    travel_z = TOP + 0.16
    grip_z = TOP + MARKER / 2
    drop_z = TABLE_TOP_Z + 0.01 + MARKER / 2

    def onto(colour: str):
        (mx, my), _ = MARKERS[colour]
        (tx, ty), _ = TABLES[TARGET[colour]]
        plan = pick_place_waypoints((mx, my, grip_z), (tx, ty, drop_z), travel_z=travel_z)
        hover = plan[0]
        return [hover, Waypoint(2.5, hover.pos, FINGER_OPEN, "wait", hover.yaw), *plan[1:]]

    left = onto("blue") + [Waypoint(1.5, (0.18, 0.30, travel_z), FINGER_OPEN, "out of the way", 0.0)]
    left_time = sum(w.duration for w in left)
    right_ready = (0.318, -0.298, TOP + 0.257)
    right = [Waypoint(left_time, right_ready, FINGER_OPEN, "wait for the left arm", 0.0), *onto("red")]
    right.append(Waypoint(1.5, (0.10, -0.28, travel_z), FINGER_OPEN, "out of the way", 0.0))
    return {"left": left, "right": right}
