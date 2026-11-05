"""On the station table: three machines, each a loading fixture with a stack light behind it. The left light shows
green (ready), the middle red, the right amber. The part goes on the fixture of the machine that is ready. The
machines are fixed; the part is loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "load the part onto the machine that is ready" --scorer task_score ...
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


# -- three machines: a loading fixture each, with a stack light behind it ---------------------------------------
# Each stack light is a post with three lamps, red on top, amber in the middle and green at the bottom; one lamp
# per light is lit (bright), the other two are off (dark).
PAD, PAD_T = 0.10, 0.006
PAD_X = 0.33
MACHINES = {"m_left": 0.15, "m_middle": 0.0, "m_right": -0.15}  # y, named as seen from behind the arms
LIT = {"m_left": "green", "m_middle": "red", "m_right": "amber"}
READY = "m_left"  # green: ready to load
LAMP_ON = {"red": (0.95, 0.10, 0.08), "amber": (1.0, 0.62, 0.05), "green": (0.10, 0.95, 0.25)}
LAMP_OFF = {"red": (0.28, 0.10, 0.10), "amber": (0.30, 0.22, 0.08), "green": (0.08, 0.26, 0.12)}
LAMP_ORDER = ("green", "amber", "red")  # bottom to top
LIGHT_X, POST_H, LAMP_R, LAMP_H = 0.43, 0.06, 0.02, 0.03
STEEL = (0.62, 0.64, 0.68)


def machine(name: str, y: float) -> list:
    parts = [
        Box(f"{name}_fixture", pos=(PAD_X, y, TOP + PAD_T / 2), size=(PAD, PAD, PAD_T), color=(0.40, 0.42, 0.46)),
        Cylinder(f"{name}_post", pos=(LIGHT_X, y, TOP + POST_H / 2), radius=0.008, height=POST_H, color=STEEL),
    ]
    for i, colour in enumerate(LAMP_ORDER):
        shade = LAMP_ON[colour] if LIT[name] == colour else LAMP_OFF[colour]
        parts.append(Cylinder(f"{name}_lamp_{colour}", pos=(LIGHT_X, y, TOP + POST_H + (i + 0.5) * LAMP_H),
                              radius=LAMP_R, height=LAMP_H, color=shade))
    return parts


PART, PART_MASS = 0.04, 0.17
PART_START = (0.10, 0.08)
OBJECTS = [part for n, y in MACHINES.items() for part in machine(n, y)]
OBJECTS.append(Box("part", pos=(*PART_START, TOP + PART / 2), size=(PART,) * 3, color=(0.25, 0.27, 0.30),
                   mass=PART_MASS))

# -- scoring ----------------------------------------------------------------------------------------------------


def loaded_on(state):
    """The machine whose fixture the part's centre is over (within the fixture's edges) while resting on it, or
    None."""
    x, y, z = (float(v) for v in state.pos)
    if abs(x - PAD_X) >= PAD / 2 or z > TOP + PAD_T + PART / 2 + 0.02:
        return None
    return next((n for n, my in MACHINES.items() if abs(y - my) < PAD / 2), None)


def outcome(objects) -> str:
    """The machine the part is loaded on ('m_left', 'm_middle', 'm_right') or 'none'."""
    return loaded_on(objects["part"]) or "none"


def success(objects):
    return outcome(objects) == READY and objects["part"].resting()


def distance(objects):
    x, y, _ = (float(v) for v in objects["part"].pos)
    return ((x - PAD_X) ** 2 + (y - MACHINES[READY]) ** 2) ** 0.5


def score(objects):
    """1.0 if the part is on the fixture of the machine with the green light; 0 otherwise."""
    return 1.0 if outcome(objects) == READY else 0.0


def demo():
    """The left arm picks up the part, pausing 2.5 s above it, and sets it on the left machine's fixture."""
    travel_z = TOP + 0.16
    z = TOP + PART / 2
    plan = pick_place_waypoints((*PART_START, z), (PAD_X, MACHINES[READY], TOP + PAD_T + PART / 2 + 0.005),
                                travel_z=travel_z)
    left = with_wait(plan) + [Waypoint(1.5, (0.12, 0.28, travel_z), FINGER_OPEN, "out of the way", 0.0)]
    return {"left": left}
