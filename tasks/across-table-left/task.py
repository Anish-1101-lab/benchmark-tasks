"""On the station table: three identical cork coasters in a row, a red cup in front of them, and a place setting at
the far side of the table where the person sits, facing the arms. The person asks for the cup on the coaster on
*their* left, which is the arms' right. The coasters and the place setting are fixed; the cup is loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "i'm sitting across the table from you. put the cup on the coaster on my left" --scorer task_score ...
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


# -- the coasters, the place setting and the cup ----------------------------------------------------------------
# Three identical cork coasters in a row across the table, named as seen from behind the arms. The person sits at
# the far side of the table, facing the arms, behind their place setting: their left is the arms' right.
COASTER_R, COASTER_T = 0.045, 0.004
CORK = (0.66, 0.50, 0.33)
COASTERS = {"arms_left": (0.30, 0.15), "middle": (0.30, 0.0), "arms_right": (0.30, -0.15)}
TARGET = "arms_right"  # the person's left
PLATE = Cylinder("place_plate", pos=(0.47, 0.0, TOP + 0.006), radius=0.07, height=0.012, color=WHITE)
CUP_R, CUP_H, CUP_MASS = 0.03, 0.08, 0.08
CUP_START = (0.12, -0.05)
CUP = Cylinder("cup", pos=(*CUP_START, TOP + CUP_H / 2), radius=CUP_R, height=CUP_H, color=(0.80, 0.22, 0.20),
               mass=CUP_MASS)
OBJECTS = [
    *[Cylinder(f"coaster_{n}", pos=(x, y, TOP + COASTER_T / 2), radius=COASTER_R, height=COASTER_T, color=CORK)
      for n, (x, y) in COASTERS.items()],
    PLATE,
    CUP,
]

# -- scoring ----------------------------------------------------------------------------------------------------


def upright(state) -> bool:
    """The cup's axis is within about 25 degrees of vertical."""
    qx, qy, _, _ = (float(v) for v in state.quat_xyzw)
    return 1 - 2 * (qx * qx + qy * qy) > 0.9


def on_coaster(state):
    """The coaster under the cup's centre (within the coaster's radius), or None."""
    x, y, z = (float(v) for v in state.pos)
    if z > TOP + COASTER_T + CUP_H / 2 + 0.02:
        return None
    return next((n for n, (cx, cy) in COASTERS.items() if (x - cx) ** 2 + (y - cy) ** 2 < COASTER_R**2), None)


def outcome(objects) -> str:
    """'persons_left', 'middle', 'persons_right' (the coaster the cup stands on), 'tipped' or 'none'."""
    cup = objects["cup"]
    where = on_coaster(cup)
    if where is None:
        return "none"
    if not upright(cup):
        return "tipped"
    return {"arms_right": "persons_left", "middle": "middle", "arms_left": "persons_right"}[where]


def success(objects):
    return outcome(objects) == "persons_left" and objects["cup"].resting()


def distance(objects):
    x, y, _ = (float(v) for v in objects["cup"].pos)
    tx, ty = COASTERS[TARGET]
    return ((x - tx) ** 2 + (y - ty) ** 2) ** 0.5


def score(objects):
    """1.0 if the cup stands upright on the coaster on the person's left (the arms' right); 0 otherwise."""
    return 1.0 if outcome(objects) == "persons_left" else 0.0


def demo():
    """The right arm picks up the cup, pausing 2.5 s above it, and sets it down on the coaster on the arms' right."""
    travel_z = TOP + 0.18
    tx, ty = COASTERS[TARGET]
    plan = pick_place_waypoints((*CUP_START, TOP + CUP_H / 2), (tx, ty, TOP + COASTER_T + CUP_H / 2 + 0.005),
                                travel_z=travel_z)
    right = with_wait(plan) + [Waypoint(1.5, (0.12, -0.26, travel_z), FINGER_OPEN, "out of the way", 0.0)]
    return {"right": right}
