"""On the station table: three red cans alike but for height (6, 9 and 12 cm) standing in a row, medium, tall,
short, and three square marks on a shelf strip behind them. They go on the marks shortest on the left to
tallest on the right. The shelf and marks are fixed; the cans are loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "put the cans on the shelf marks from shortest on the left to tallest on the right" --scorer task_score ...
"""

from yam_arena.demo import FINGER_OPEN, Waypoint, pick_place_waypoints
from yam_arena.task_file import TABLE_TOP, Box, Cylinder

SCENE = "station"
TOP = TABLE_TOP[SCENE]
WHITE = (0.95, 0.95, 0.95)
BLACK = (0.05, 0.05, 0.05)
RIGHT_READY = (0.318, -0.298, TOP + 0.257)  # the right arm's ready pose (TCP)
LEFT_READY = (0.318, 0.298, TOP + 0.257)

# -- 5 x 7 block characters -------------------------------------------------------------------------------------
GLYPHS = {
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    " ": (".....",) * 7,
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


def card(name, text, centre_xy, cell=0.005, ink=BLACK, paper=WHITE, base_z=None):
    """A card lying flat with ``text`` printed on it, readable from behind the arms (tops toward +x, reading from +y
    to -y), one cell of margin all round."""
    base = TOP if base_z is None else base_z
    cols, rows = len(text) * 6 + 1, 9
    cx, cy = centre_xy
    depth, width = rows * cell, cols * cell
    parts = [Box(name, pos=(cx, cy, base + 0.0015), size=(depth, width, 0.003), color=paper)]
    top_x, left_y = cx + depth / 2 - cell, cy + width / 2 - cell
    k = 0
    for i, ch in enumerate(text):
        for r, c, h, w in _glyph_rects(GLYPHS[ch]):
            x = top_x - (r + h / 2) * cell
            y = left_y - (i * 6 + c + w / 2) * cell
            parts.append(Box(f"{name}_ink_{k}", pos=(x, y, base + 0.0035), size=(h * cell, w * cell, 0.001), color=ink))
            k += 1
    return parts


def open_box(name, centre_xy, inner, wall_h, color, wall=0.004, floor_t=0.003):
    """A fixed open-topped box: ``inner`` is its inside (x, y) size; returns the parts and the floor height."""
    (cx, cy), (ix, iy) = centre_xy, inner
    h = TOP + floor_t + wall_h / 2
    ox, oy = ix + 2 * wall, iy + 2 * wall
    return [
        Box(f"{name}_floor", pos=(cx, cy, TOP + floor_t / 2), size=(ox, oy, floor_t), color=color),
        Box(f"{name}_front", pos=(cx - ix / 2 - wall / 2, cy, h), size=(wall, oy, wall_h), color=color),
        Box(f"{name}_back", pos=(cx + ix / 2 + wall / 2, cy, h), size=(wall, oy, wall_h), color=color),
        Box(f"{name}_left", pos=(cx, cy + iy / 2 + wall / 2, h), size=(ix, wall, wall_h), color=color),
        Box(f"{name}_right", pos=(cx, cy - iy / 2 - wall / 2, h), size=(ix, wall, wall_h), color=color),
    ]


def inside(state, centre_xy, inner, top_z) -> bool:
    """The object's centre is inside the walls, below their tops."""
    x, y, z = (float(v) for v in state.pos)
    return abs(x - centre_xy[0]) < inner[0] / 2 and abs(y - centre_xy[1]) < inner[1] / 2 and z < top_z


def with_wait(plan):
    """Pause 2.5 s at the hover point before descending to grip."""
    hover = plan[0]
    return [hover, Waypoint(2.5, hover.pos, FINGER_OPEN, "wait", hover.yaw), *plan[1:]]


def duration(plan) -> float:
    return sum(w.duration for w in plan)


# -- the cans and the shelf marks -------------------------------------------------------------------------------
# Three cans of one product line, alike but for height, stand in a row; three square marks on the shelf, left to
# right as seen from behind the arms, are where they go, shortest on the left.
CAN_R = 0.025
CANS = {"short": 0.06, "medium": 0.09, "tall": 0.12}  # heights (m)
CAN_MASS = {"short": 0.08, "medium": 0.12, "tall": 0.16}
START_X = 0.12
START_Y = {"medium": 0.12, "tall": 0.0, "short": -0.12}  # left to right: medium, tall, short
MARK, MARK_T, MARK_X = 0.07, 0.002, 0.33
MARKS = {"short": 0.11, "medium": 0.0, "tall": -0.11}  # left mark: shortest
CAN_RED = (0.78, 0.15, 0.15)
SHELF = Box("shelf", pos=(MARK_X, 0.0, TOP + 0.001), size=(0.12, 0.36, 0.002), color=(0.55, 0.42, 0.30))
OBJECTS = [
    SHELF,
    *[Box(f"mark_{n}", pos=(MARK_X, y, TOP + 0.002 + MARK_T / 2), size=(MARK, MARK, MARK_T), color=WHITE)
      for n, y in MARKS.items()],
    *[Cylinder(f"can_{n}", pos=(START_X, START_Y[n], TOP + h / 2), radius=CAN_R, height=h, color=CAN_RED,
               mass=CAN_MASS[n]) for n, h in CANS.items()],
]
SURFACE = TOP + 0.002 + MARK_T

# -- scoring ----------------------------------------------------------------------------------------------------


def upright(state) -> bool:
    qx, qy, _, _ = (float(v) for v in state.quat_xyzw)
    return 1 - 2 * (qx * qx + qy * qy) > 0.9


def on_mark(name: str, state):
    """The mark the can stands upright on (its centre within the mark's edges), or None."""
    x, y, z = (float(v) for v in state.pos)
    if not upright(state) or z > SURFACE + CANS[name] / 2 + 0.02 or abs(x - MARK_X) >= MARK / 2:
        return None
    return next((m for m, my in MARKS.items() if abs(y - my) < MARK / 2), None)


def outcome(objects) -> str:
    """'sorted' (every can on its own mark), or 'n_placed': how many cans stand on any mark, in whatever order."""
    where = {n: on_mark(n, objects[f"can_{n}"]) for n in CANS}
    if all(where[n] == n for n in CANS):
        return "sorted"
    return f"{sum(w is not None for w in where.values())}_placed"


def success(objects):
    return outcome(objects) == "sorted" and all(objects[f"can_{n}"].resting() for n in CANS)


def distance(objects):
    return float(sum(on_mark(n, objects[f"can_{n}"]) != n for n in CANS))


def score(objects):
    """1.0 if each can stands upright on its mark, shortest on the left and tallest on the right; 0 otherwise. No
    partial credit: three cans set on the marks at random are in order one time in six, and a single can on its mark
    one time in three."""
    return 1.0 if outcome(objects) == "sorted" else 0.0


AIM_DY = {"short": 0.016, "medium": 0.0, "tall": 0.0}  # the cans slip sideways in the grip; measured in a demo run


def demo():
    """The arms take turns: the left arm puts the medium can on the middle mark and moves aside while the right arm
    waits at its ready pose; then the right arm puts the tall can on the right mark and the short can on the left
    mark. Each grip pauses 2.5 s above the can and closes at its mid-height; the right arm aims 1.6 cm left of the
    left mark to make up for the short can's slip in its grip."""
    travel_z = TOP + 0.24

    def put(n):
        h = CANS[n]
        place = (MARK_X, MARKS[n] + AIM_DY[n], SURFACE + h / 2 + 0.005)
        return with_wait(pick_place_waypoints((START_X, START_Y[n], TOP + h / 2), place, travel_z=travel_z))

    left = put("medium") + [Waypoint(1.5, (0.12, 0.30, travel_z), FINGER_OPEN, "out of the way", 0.0)]
    right = [Waypoint(duration(left), RIGHT_READY, FINGER_OPEN, "wait for the left arm", 0.0)]
    right += put("tall") + put("short")
    right.append(Waypoint(1.5, (0.10, -0.28, travel_z), FINGER_OPEN, "out of the way", 0.0))
    return {"left": left, "right": right}
