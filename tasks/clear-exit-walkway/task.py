"""On the station table: a green walkway marked along the arms' midline to an EXIT sign at the far end, with two
cardboard boxes standing on it and a third beside it. Clearing the walkway means moving both boxes off it,
without pushing them off the table or moving the third onto it. The walkway and sign are fixed; the boxes are loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "move the boxes off the walkway to the emergency exit" --scorer task_score ...
"""

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


# -- the walkway, the exit sign and the boxes -------------------------------------------------------------------
GREEN, DARK_GREEN = (0.20, 0.62, 0.30), (0.05, 0.40, 0.18)
WALK_W, WALK_X0, WALK_X1 = 0.12, 0.04, 0.46  # a marked walkway along the arms' midline, near end to far end
WALKWAY = Box("walkway", pos=((WALK_X0 + WALK_X1) / 2, 0.0, TOP + 0.001), size=(WALK_X1 - WALK_X0, WALK_W, 0.002),
              color=GREEN)
EXIT_SIGN = card("exit_sign", "EXIT", (0.50, 0.0), cell=0.005, ink=WHITE, paper=DARK_GREEN)
BOX_SIZE, BOX_MASS = 0.06, 0.10
CARDBOARD = (0.72, 0.56, 0.36)
BOXES = {"near": (0.15, 0.0), "far": (0.31, 0.0), "side": (0.23, 0.20)}  # "side" already sits clear of the walkway
OBJECTS = [
    WALKWAY,
    *EXIT_SIGN,
    *[Box(f"box_{n}", pos=(x, y, TOP + BOX_SIZE / 2), size=(BOX_SIZE,) * 3, color=CARDBOARD, mass=BOX_MASS)
      for n, (x, y) in BOXES.items()],
]

# -- scoring ----------------------------------------------------------------------------------------------------


def lost(state) -> bool:
    """The box has fallen off the table."""
    return float(state.pos[2]) < TOP - 0.02


def blocking(state) -> bool:
    """Any part of the box's footprint (centre within half a box width plus 1.2 cm of margin) is over the
    walkway."""
    x, y, _ = (float(v) for v in state.pos)
    reach = BOX_SIZE / 2 + 0.012
    return abs(y) < WALK_W / 2 + reach and WALK_X0 - reach < x < WALK_X1 + reach


def outcome(objects) -> str:
    """'lost' if any box fell off the table; otherwise 'n_blocking' boxes still over the walkway."""
    if any(lost(objects[f"box_{n}"]) for n in BOXES):
        return "lost"
    return f"{sum(blocking(objects[f'box_{n}']) for n in BOXES)}_blocking"


def success(objects):
    return outcome(objects) == "0_blocking" and all(objects[f"box_{n}"].resting() for n in BOXES)


def distance(objects):
    return float(sum(blocking(objects[f"box_{n}"]) or lost(objects[f"box_{n}"]) for n in BOXES))


def score(objects):
    """1.0 with no box over the walkway; 0.5 with one; 0 with two or more, or if any box fell off the table."""
    return {"0_blocking": 1.0, "1_blocking": 0.5}.get(outcome(objects), 0.0)


def demo():
    """The arms take turns: the left arm sets the near box down to the walkway's left while the right arm waits at
    its ready pose, then the right arm sets the far box down to its right. Each grip pauses 2.5 s above the box."""
    travel_z = TOP + 0.16
    z = TOP + BOX_SIZE / 2
    left = with_wait(pick_place_waypoints((*BOXES["near"], z), (0.10, 0.17, z + 0.005), travel_z=travel_z))
    left.append(Waypoint(1.5, (0.10, 0.30, travel_z), FINGER_OPEN, "out of the way", 0.0))
    right = [Waypoint(duration(left), RIGHT_READY, FINGER_OPEN, "wait for the left arm", 0.0)]
    right += with_wait(pick_place_waypoints((*BOXES["far"], z), (0.31, -0.18, z + 0.005), travel_z=travel_z))
    right.append(Waypoint(1.5, (0.12, -0.28, travel_z), FINGER_OPEN, "out of the way", 0.0))
    return {"left": left, "right": right}
