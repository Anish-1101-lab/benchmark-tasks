"""On the station table: three pressure gauges facing up, each with a grey tag spot in front of it, and a red tag.
The left gauge reads 90 % of full scale, in its red zone (the last 20 %); the others read 45 % and 68 %. The tag
goes on the spot of the gauge reading in the red zone. Gauges and spots are fixed; the tag is loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "put the red tag in front of the gauge reading in the red zone" --scorer task_score ...
"""

import math

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


# -- three pressure gauges, a tag spot in front of each, and the red tag ----------------------------------------
# Each gauge faces up: a white dial in a black rim, scale from lower left (0) clockwise over the top to lower right
# (full scale) as seen from behind the arms, the last 20 % of the scale marked in red, and a black needle.
DIAL_R, RIM_R = 0.042, 0.048
GAUGE_X = 0.40
GAUGES = {"g_left": 0.15, "g_middle": 0.0, "g_right": -0.15}  # y, named as seen from behind the arms
READING = {"g_left": 0.90, "g_middle": 0.45, "g_right": 0.68}  # fraction of full scale
RED_FROM = 0.80
IN_RED = "g_left"
SWEEP = math.radians(270)
START = math.radians(135)  # angle of zero on the table (from +x toward +y): lower left, seen from behind the arms


def dial_angle(frac: float) -> float:
    return START - frac * SWEEP  # clockwise, seen from above


def gauge(name: str, y: float) -> list:
    z = TOP + 0.008
    parts = [
        Cylinder(f"{name}_rim", pos=(GAUGE_X, y, TOP + 0.003), radius=RIM_R, height=0.006, color=BLACK),
        Cylinder(f"{name}_dial", pos=(GAUGE_X, y, TOP + 0.0065), radius=DIAL_R, height=0.001, color=WHITE),
    ]
    for k in range(11):  # scale ticks every 10 %
        a = dial_angle(k / 10)
        r = DIAL_R - 0.006
        parts.append(Box(f"{name}_tick_{k}", pos=(GAUGE_X + r * math.cos(a), y + r * math.sin(a), z - 0.001),
                         size=(0.008, 0.0015, 0.001), color=BLACK, yaw=a))
    for k in range(6):  # the red zone: an arc of short red bars
        a = dial_angle(RED_FROM + (k + 0.5) * (1 - RED_FROM) / 6)
        r = DIAL_R - 0.004
        parts.append(Box(f"{name}_red_{k}", pos=(GAUGE_X + r * math.cos(a), y + r * math.sin(a), z - 0.0012),
                         size=(0.006, 0.0095, 0.0008), color=(0.88, 0.10, 0.08), yaw=a))
    a, length = dial_angle(READING[name]), 0.034
    parts.append(Box(f"{name}_needle", pos=(GAUGE_X + length / 2 * math.cos(a), y + length / 2 * math.sin(a), z),
                     size=(length, 0.003, 0.001), color=BLACK, yaw=a))
    parts.append(Cylinder(f"{name}_hub", pos=(GAUGE_X, y, z + 0.0005), radius=0.004, height=0.002, color=BLACK))
    return parts


SPOT, SPOT_T, SPOT_X = 0.07, 0.003, 0.27
TAG, TAG_MASS = (0.05, 0.03, 0.02), 0.03
TAG_START = (0.10, 0.06)
OBJECTS = [part for n, y in GAUGES.items() for part in gauge(n, y)]
OBJECTS += [Box(f"spot_{n}", pos=(SPOT_X, y, TOP + SPOT_T / 2), size=(SPOT, SPOT, SPOT_T), color=(0.75, 0.77, 0.80))
            for n, y in GAUGES.items()]
OBJECTS.append(Box("tag", pos=(*TAG_START, TOP + TAG[2] / 2), size=TAG, color=(0.90, 0.12, 0.10), mass=TAG_MASS))

# -- scoring ----------------------------------------------------------------------------------------------------


def on_spot(state):
    """The gauge whose tag spot the tag's centre is over (within the spot's edges) while resting on it, or None."""
    x, y, z = (float(v) for v in state.pos)
    if abs(x - SPOT_X) >= SPOT / 2 or z > TOP + SPOT_T + TAG[2] / 2 + 0.02:
        return None
    return next((n for n, gy in GAUGES.items() if abs(y - gy) < SPOT / 2), None)


def outcome(objects) -> str:
    """The gauge the tag was put in front of ('g_left', 'g_middle', 'g_right') or 'none'."""
    return on_spot(objects["tag"]) or "none"


def success(objects):
    return outcome(objects) == IN_RED and objects["tag"].resting()


def distance(objects):
    x, y, _ = (float(v) for v in objects["tag"].pos)
    return ((x - SPOT_X) ** 2 + (y - GAUGES[IN_RED]) ** 2) ** 0.5


def score(objects):
    """1.0 if the tag is on the spot in front of the gauge reading in the red zone; 0 otherwise."""
    return 1.0 if outcome(objects) == IN_RED else 0.0


def demo():
    """The left arm picks up the tag, pausing 2.5 s above it, and sets it on the left gauge's tag spot."""
    travel_z = TOP + 0.14
    z = TOP + TAG[2] / 2
    plan = pick_place_waypoints((*TAG_START, z), (SPOT_X, GAUGES[IN_RED], TOP + SPOT_T + TAG[2] / 2 + 0.004),
                                travel_z=travel_z)
    left = with_wait(plan) + [Waypoint(1.5, (0.12, 0.28, travel_z), FINGER_OPEN, "out of the way", 0.0)]
    return {"left": left}
