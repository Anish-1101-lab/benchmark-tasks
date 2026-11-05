"""On the station table: three quarry tiles on a tray, two intact and one broken in two, and an open packing box
behind the tray. Only the intact tiles go in the box. The tray and box are fixed; the tiles and halves are loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "pack the undamaged tiles in the box" --scorer task_score ...
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


# -- the tray and the tiles -------------------------------------------------------------------------------------
TRAY_H = 0.03  # a fixed block the tiles lie on, so the fingers can close around them clear of the table
TRAY = Box("tray", pos=(0.17, 0.0, TOP + TRAY_H / 2), size=(0.14, 0.40, TRAY_H), color=(0.30, 0.32, 0.36))
TRAY_TOP = TOP + TRAY_H
TILE, TILE_T, TILE_MASS = 0.05, 0.02, 0.10  # 5 x 5 cm quarry tiles, 2 cm thick
TERRACOTTA = (0.74, 0.36, 0.22)
TILE_X = 0.17
INTACT = {"t1": 0.12, "t2": 0.0}  # y of each intact tile
BROKEN_Y = -0.12  # the third tile is broken in two along its middle; the halves lie 4 mm apart, slightly askew
GAP = 0.004
HALF = (TILE, (TILE - GAP) / 2, TILE_T)
BROKEN = {
    "b1": (TILE_X + 0.002, BROKEN_Y + (TILE + GAP) / 4, 0.06),
    "b2": (TILE_X - 0.002, BROKEN_Y - (TILE + GAP) / 4, -0.04),
}
OBJECTS = [
    TRAY,
    *[Box(f"tile_{n}", pos=(TILE_X, y, TRAY_TOP + TILE_T / 2), size=(TILE, TILE, TILE_T), color=TERRACOTTA,
          mass=TILE_MASS) for n, y in INTACT.items()],
    *[Box(f"half_{n}", pos=(x, y, TRAY_TOP + TILE_T / 2), size=HALF, color=TERRACOTTA, mass=TILE_MASS / 2, yaw=a)
      for n, (x, y, a) in BROKEN.items()],
]

# -- the packing box --------------------------------------------------------------------------------------------
BOX_XY, BOX_IN, WALL_H = (0.37, 0.0), (0.13, 0.13), 0.05
FLOOR = TOP + 0.003
OBJECTS += open_box("box", BOX_XY, BOX_IN, WALL_H, (0.80, 0.70, 0.52))

# -- scoring ----------------------------------------------------------------------------------------------------


def packed(objects) -> tuple[set[str], set[str]]:
    """(intact tiles in the box, broken halves in the box)."""
    top = FLOOR + WALL_H
    return ({n for n in INTACT if inside(objects[f"tile_{n}"], BOX_XY, BOX_IN, top)},
            {n for n in BROKEN if inside(objects[f"half_{n}"], BOX_XY, BOX_IN, top)})


def outcome(objects) -> str:
    """'broken_packed' if either half of the broken tile is in the box; otherwise 'n_of_2' intact tiles in it."""
    good, bad = packed(objects)
    return "broken_packed" if bad else f"{len(good)}_of_2"


def success(objects):
    return outcome(objects) == "2_of_2" and all(objects[f"tile_{n}"].resting() for n in INTACT)


def distance(objects):
    good, bad = packed(objects)
    return float(len(INTACT) - len(good) + len(bad))


def score(objects):
    """1.0 if both intact tiles are in the box and no part of the broken one is; 0 otherwise. No partial credit: a
    tile picked at random is intact two times in three."""
    return 1.0 if outcome(objects) == "2_of_2" else 0.0


def demo():
    """The arms take turns: the left arm packs tile t1 and moves aside while the right arm waits at its ready pose;
    then the right arm packs tile t2. Each grip pauses 2.5 s above the tile and closes across it at mid-thickness."""
    travel_z = TOP + 0.16
    grip_z = TRAY_TOP + TILE_T / 2
    drop_z = FLOOR + WALL_H + 0.015 + TILE_T / 2

    def pack(n, dy):
        return with_wait(pick_place_waypoints((TILE_X, INTACT[n], grip_z), (BOX_XY[0], BOX_XY[1] + dy, drop_z),
                                              travel_z=travel_z))

    left = pack("t1", 0.03) + [Waypoint(1.5, (0.18, 0.30, travel_z), FINGER_OPEN, "out of the way", 0.0)]
    right = [Waypoint(duration(left), RIGHT_READY, FINGER_OPEN, "wait for the left arm", 0.0), *pack("t2", -0.03)]
    right.append(Waypoint(1.5, (0.10, -0.28, travel_z), FINGER_OPEN, "out of the way", 0.0))
    return {"left": left, "right": right}
