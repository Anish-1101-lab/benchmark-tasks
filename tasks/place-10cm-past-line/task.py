"""On the station table: a red line taped across the table, a centimetre ruler lying from the line outward, and a
blue block in front of the line. The block goes down with its centre 10 cm beyond the line, measured square to
it, anywhere along it. The line and ruler are fixed; the block is loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "put the block down with its centre 10 cm beyond the red line" --scorer task_score ...
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


# -- the reference line, the ruler and the block ----------------------------------------------------------------
LINE_X, LINE_W = 0.12, 0.006  # a red line taped across the table, square to the arms' midline
LINE = Box("red_line", pos=(LINE_X, 0.0, TOP + 0.001), size=(LINE_W, 0.50, 0.002), color=(0.85, 0.12, 0.10))
OFFSET = 0.10  # the instruction's 10 cm, from the line's centre to the block's centre
# A white ruler lying flat from the line's centre outward, on the arms' left: a black tick every centimetre (1 cm
# long), every 5 cm (2 cm long), with 5, 10, 15 and 20 printed beside the long ticks.
RULER_Y, RULER_W, RULER_L = 0.15, 0.045, 0.22
RULER = [Box("ruler", pos=(LINE_X + RULER_L / 2, RULER_Y, TOP + 0.0015), size=(RULER_L, RULER_W, 0.003),
             color=WHITE)]
for cm in range(0, 22):
    tick = 0.02 if cm % 5 == 0 else 0.01
    RULER.append(Box(f"ruler_tick_{cm}", pos=(LINE_X + cm / 100, RULER_Y - RULER_W / 2 + tick / 2, TOP + 0.0035),
                     size=(0.0015, tick, 0.001), color=BLACK))
    if cm % 5 == 0 and cm:
        RULER += card(f"ruler_{cm}", str(cm), (LINE_X + cm / 100, RULER_Y + 0.011), cell=0.0016, base_z=TOP + 0.003)[1:]
BLOCK, BLOCK_MASS = 0.04, 0.04
BLOCK_START = (0.07, -0.10)
OBJECTS = [LINE, *RULER,
           Box("block", pos=(*BLOCK_START, TOP + BLOCK / 2), size=(BLOCK,) * 3, color=(0.20, 0.38, 0.80),
               mass=BLOCK_MASS)]

# -- scoring ----------------------------------------------------------------------------------------------------


def error(objects) -> float:
    """How far the block's centre is from 10 cm beyond the line's centre, measured square to the line (m)."""
    return abs(float(objects["block"].pos[0]) - LINE_X - OFFSET)


def on_table(objects) -> bool:
    """The block rests on the table (or on the ruler), not held up or fallen off."""
    return TOP < float(objects["block"].pos[2]) < TOP + BLOCK / 2 + 0.008


def outcome(objects) -> str:
    """'within_1cm', 'within_2cm', 'off' (on the table, further off), or 'not_on_table'."""
    if not on_table(objects):
        return "not_on_table"
    e = error(objects)
    return "within_1cm" if e <= 0.01 else "within_2cm" if e <= 0.02 else "off"


def success(objects):
    return outcome(objects) == "within_1cm" and objects["block"].resting()


def distance(objects):
    return error(objects)


def score(objects):
    """1.0 with the block's centre within 1 cm of 10 cm beyond the line; 0.5 within 2 cm; 0 otherwise or if it isn't
    resting on the table."""
    return {"within_1cm": 1.0, "within_2cm": 0.5}.get(outcome(objects), 0.0)


AIM_DX = 0.0  # correction for the block's slip in the grip, measured in the demo run


def demo():
    """The right arm picks up the block, pausing 2.5 s above it, and sets it down 10 cm beyond the line, in line
    with where it started."""
    travel_z = TOP + 0.14
    z = TOP + BLOCK / 2
    place = (LINE_X + OFFSET + AIM_DX, BLOCK_START[1], z + 0.004)
    right = with_wait(pick_place_waypoints((*BLOCK_START, z), place, travel_z=travel_z))
    right.append(Waypoint(1.5, (0.12, -0.28, travel_z), FINGER_OPEN, "out of the way", 0.0))
    return {"right": right}
