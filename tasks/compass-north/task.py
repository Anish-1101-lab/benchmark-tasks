"""On the station table: a grey plate with an identical white pad on each side, a compass card whose arrow shows
north pointing to the arms' left, and a red cube. The pad north of the plate is the one on its left, not the
one beyond it. The plate, pads and card are fixed; the cube is loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "put the cube on the pad north of the plate" --scorer task_score ...
"""

import math

from yam_arena.demo import FINGER_OPEN, Waypoint, pick_place_waypoints
from yam_arena.task_file import TABLE_TOP, Box

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


# -- the plate, the four pads and the compass card --------------------------------------------------------------
# A grey plate with an identical white pad on each of its four sides. The compass card shows north toward the
# arms' left (+y), so the pad north of the plate is the one on its left, not the one beyond it.
PLATE_XY, OFFSET = (0.28, 0.0), 0.11
PLATE = Box("plate", pos=(*PLATE_XY, TOP + 0.005), size=(0.08, 0.08, 0.01), color=(0.45, 0.47, 0.50))
PAD, PAD_T = 0.07, 0.003
PADS = {  # compass direction: (x, y)
    "north": (PLATE_XY[0], PLATE_XY[1] + OFFSET),
    "east": (PLATE_XY[0] + OFFSET, PLATE_XY[1]),
    "south": (PLATE_XY[0], PLATE_XY[1] - OFFSET),
    "west": (PLATE_XY[0] - OFFSET, PLATE_XY[1]),
}
NORTH = (0.0, 1.0)  # unit vector on the table: north points to the arms' left
ROSE_XY, ROSE_SIZE = (0.11, 0.24), 0.13


def compass_card() -> list[Box]:
    """A white card with a black cross, a long arrow toward north, and the letters N, E, S and W at the ends."""
    cx, cy = ROSE_XY
    z = TOP + 0.0035
    parts = [Box("rose_card", pos=(cx, cy, TOP + 0.0015), size=(ROSE_SIZE, ROSE_SIZE, 0.003), color=WHITE)]
    nx, ny = NORTH
    ex, ey = ny, -nx  # east is a quarter turn clockwise from north, seen from above
    arm = 0.035
    yaw_n = math.atan2(ny, nx)
    parts.append(Box("rose_ns", pos=(cx, cy, z), size=(2 * arm, 0.004, 0.001), color=BLACK, yaw=yaw_n))
    parts.append(Box("rose_ew", pos=(cx, cy, z), size=(2 * arm, 0.004, 0.001), color=BLACK, yaw=yaw_n - math.pi / 2))
    tip = (cx + nx * arm, cy + ny * arm)
    for k, side in enumerate((1, -1)):  # the arrowhead's two strokes, swept back 35 degrees from the tip
        a = yaw_n + math.pi + side * math.radians(35)
        parts.append(Box(f"rose_head_{k}", pos=(tip[0] + math.cos(a) * 0.009, tip[1] + math.sin(a) * 0.009, z),
                         size=(0.018, 0.004, 0.001), color=BLACK, yaw=a))
    for letter, (dx, dy) in {"N": (nx, ny), "E": (ex, ey), "S": (-nx, -ny), "W": (-ex, -ey)}.items():
        parts += card(f"rose_{letter}", letter, (cx + dx * 0.05, cy + dy * 0.05), cell=0.0025)[1:]
    return parts


CUBE, CUBE_MASS = 0.04, 0.06
CUBE_START = (0.08, 0.0)
OBJECTS = [
    PLATE,
    *[Box(f"pad_{n}", pos=(x, y, TOP + PAD_T / 2), size=(PAD, PAD, PAD_T), color=WHITE) for n, (x, y) in PADS.items()],
    *compass_card(),
    Box("cube", pos=(*CUBE_START, TOP + CUBE / 2), size=(CUBE,) * 3, color=(0.85, 0.20, 0.18), mass=CUBE_MASS),
]

# -- scoring ----------------------------------------------------------------------------------------------------


def on_pad(state):
    """The pad the cube's centre is over (within the pad's edges) while resting on it, or None."""
    x, y, z = (float(v) for v in state.pos)
    if z > TOP + PAD_T + CUBE / 2 + 0.02:
        return None
    return next((n for n, (px, py) in PADS.items() if abs(x - px) < PAD / 2 and abs(y - py) < PAD / 2), None)


def outcome(objects) -> str:
    """The pad the cube is on ('north', 'east', 'south', 'west') or 'none'."""
    return on_pad(objects["cube"]) or "none"


def success(objects):
    return outcome(objects) == "north" and objects["cube"].resting()


def distance(objects):
    x, y, _ = (float(v) for v in objects["cube"].pos)
    px, py = PADS["north"]
    return ((x - px) ** 2 + (y - py) ** 2) ** 0.5


def score(objects):
    """1.0 if the cube is on the pad north of the plate (the arms' left of it); 0 otherwise."""
    return 1.0 if outcome(objects) == "north" else 0.0


def demo():
    """The left arm picks up the cube, pausing 2.5 s above it, and sets it on the north pad."""
    travel_z = TOP + 0.16
    plan = pick_place_waypoints((*CUBE_START, TOP + CUBE / 2), (*PADS["north"], TOP + PAD_T + CUBE / 2 + 0.005),
                                travel_z=travel_z)
    left = with_wait(plan) + [Waypoint(1.5, (0.12, 0.30, travel_z), FINGER_OPEN, "out of the way", 0.0)]
    return {"left": left}
