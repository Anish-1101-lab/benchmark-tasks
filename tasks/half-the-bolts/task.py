"""On the station table: six bolts standing in a row and an open cup behind them. Half of six is three, so the cup
should end up with exactly three bolts. The cup is fixed; the bolts are loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "put half of the bolts in the cup" --scorer task_score ...
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


# -- the bolts and the cup --------------------------------------------------------------------------------------
BOLT_R, BOLT_H, BOLT_MASS = 0.008, 0.06, 0.095  # M16 x 60 mm hex bolts, modelled as steel rods standing on end
BOLT_X = 0.16
BOLTS = {f"b{i + 1}": y for i, y in enumerate((0.20, 0.12, 0.04, -0.04, -0.12, -0.20))}  # left to right
STEEL = (0.62, 0.64, 0.68)
CUP_XY, CUP_IN, WALL_H = (0.37, 0.0), (0.13, 0.13), 0.05
FLOOR = TOP + 0.003
OBJECTS = [
    *[Cylinder(f"bolt_{n}", pos=(BOLT_X, y, TOP + BOLT_H / 2), radius=BOLT_R, height=BOLT_H, color=STEEL,
               mass=BOLT_MASS) for n, y in BOLTS.items()],
    *open_box("cup", CUP_XY, CUP_IN, WALL_H, (0.18, 0.36, 0.72)),
]
HALF = len(BOLTS) // 2

# -- scoring ----------------------------------------------------------------------------------------------------


def in_cup(objects) -> int:
    return sum(inside(objects[f"bolt_{n}"], CUP_XY, CUP_IN, FLOOR + WALL_H) for n in BOLTS)


def outcome(objects) -> str:
    """'n_in_cup': how many bolts are in the cup (0 to 6)."""
    return f"{in_cup(objects)}_in_cup"


def success(objects):
    return in_cup(objects) == HALF and all(objects[f"bolt_{n}"].resting() for n in BOLTS)


def distance(objects):
    return float(abs(in_cup(objects) - HALF))


def score(objects):
    """1.0 if exactly three of the six bolts are in the cup; 0 otherwise."""
    return 1.0 if in_cup(objects) == HALF else 0.0


def demo():
    """The arms take turns: the left arm puts bolts b1 and b2 in the cup and moves aside while the right arm waits
    at its ready pose; then the right arm puts bolt b6 in. Each grip pauses 2.5 s above the bolt and closes 4 cm
    above the table."""
    travel_z = TOP + 0.16
    grip_z = TOP + 0.04
    drop_z = FLOOR + WALL_H + 0.015 + BOLT_H / 2

    def put(n, dy):
        return with_wait(pick_place_waypoints((BOLT_X, BOLTS[n], grip_z), (CUP_XY[0], CUP_XY[1] + dy, drop_z),
                                              travel_z=travel_z))

    left = put("b1", 0.04) + put("b2", 0.0)
    left.append(Waypoint(1.5, (0.18, 0.30, travel_z), FINGER_OPEN, "out of the way", 0.0))
    right = [Waypoint(duration(left), RIGHT_READY, FINGER_OPEN, "wait for the left arm", 0.0), *put("b6", -0.04)]
    right.append(Waypoint(1.5, (0.10, -0.28, travel_z), FINGER_OPEN, "out of the way", 0.0))
    return {"left": left, "right": right}
