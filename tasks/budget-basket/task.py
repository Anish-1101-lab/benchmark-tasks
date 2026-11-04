"""On the station table: four grocery boxes in a row, each with a shelf price tag in front of it (6, 3, 2 and 7
euros, left to right), and an open basket behind them. The user asks to spend exactly 10 euros. Only one set of
items adds up to 10 (the 3 and the 7), so the robot has to read the prices and add. The tags and the basket are
fixed; the boxes are loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "spend exactly 10 euros: put items in the basket so their prices add up to exactly 10" \\
           --scorer task_score ...
"""

from itertools import combinations

from yam_arena.demo import FINGER_OPEN, Waypoint, pick_place_waypoints
from yam_arena.task_file import TABLE_TOP, Box

SCENE = "station"
TOP = TABLE_TOP[SCENE]
WHITE = (0.95, 0.95, 0.95)
BLACK = (0.05, 0.05, 0.05)
BUDGET = 10

# -- 5 x 7 block digits -----------------------------------------------------------------------------------------
GLYPHS = {
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "6": (".##..", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
}
CELL, MARGIN = 0.008, 1  # 4 x 5.6 cm digits with one cell of margin


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


def tag(name: str, digit: str, centre_xy) -> list[Box]:
    """A white price tag lying flat with one black digit, readable from behind the arms."""
    cx, cy = centre_xy
    depth, width = (7 + 2 * MARGIN) * CELL, (5 + 2 * MARGIN) * CELL
    parts = [Box(name, pos=(cx, cy, TOP + 0.0015), size=(depth, width, 0.003), color=WHITE)]
    top_x, left_y = cx + depth / 2 - MARGIN * CELL, cy + width / 2 - MARGIN * CELL
    for k, (r, c, h, w) in enumerate(_glyph_rects(GLYPHS[digit])):
        parts.append(Box(f"{name}_ink_{k}", pos=(top_x - (r + h / 2) * CELL, left_y - (c + w / 2) * CELL, TOP + 0.0035),
                         size=(h * CELL, w * CELL, 0.001), color=BLACK))
    return parts


# -- the items ----------------------------------------------------------------------------------------------------
# Four 5 x 5 x 8 cm grocery boxes in a row, left to right as seen from behind the arms, each with its price tag in
# front of it (toward the arms).
ITEM = (0.05, 0.05, 0.08)
ITEM_X = 0.15
ITEMS = {  # name: (y, price, colour)
    "yellow": (0.15, 6, (0.93, 0.78, 0.15)),
    "green": (0.05, 3, (0.20, 0.60, 0.30)),
    "blue": (-0.05, 2, (0.20, 0.38, 0.80)),
    "orange": (-0.15, 7, (0.92, 0.48, 0.12)),
}
TAG_X = 0.085
BOXES = [
    Box(f"item_{n}", pos=(ITEM_X, y, TOP + ITEM[2] / 2), size=ITEM, color=col, mass=0.08)
    for n, (y, _, col) in ITEMS.items()
]
TAGS = [part for n, (y, price, _) in ITEMS.items() for part in tag(f"tag_{n}", str(price), (TAG_X, y))]

# The one set of items whose prices add up to the budget.
SOLUTIONS = [set(c) for r in range(1, len(ITEMS) + 1) for c in combinations(ITEMS, r)
             if sum(ITEMS[n][1] for n in c) == BUDGET]
assert SOLUTIONS == [{"green", "orange"}], SOLUTIONS
SOLUTION = SOLUTIONS[0]

# -- the basket ---------------------------------------------------------------------------------------------------
BASKET_XY = (0.33, 0.0)
BASKET_IN = (0.14, 0.20)  # inside, x and y
WALL, WALL_H, BASE_T = 0.004, 0.08, 0.003
FLOOR = TOP + BASE_T
BASKET_COLOR = (0.45, 0.33, 0.22)


def _basket() -> list[Box]:
    (bx, by), (ix, iy), h = BASKET_XY, BASKET_IN, FLOOR + WALL_H / 2
    ox, oy = ix + 2 * WALL, iy + 2 * WALL
    return [
        Box("basket_floor", pos=(bx, by, TOP + BASE_T / 2), size=(ox, oy, BASE_T), color=BASKET_COLOR),
        Box("basket_front", pos=(bx - ix / 2 - WALL / 2, by, h), size=(WALL, oy, WALL_H), color=BASKET_COLOR),
        Box("basket_back", pos=(bx + ix / 2 + WALL / 2, by, h), size=(WALL, oy, WALL_H), color=BASKET_COLOR),
        Box("basket_left", pos=(bx, by + iy / 2 + WALL / 2, h), size=(ix, WALL, WALL_H), color=BASKET_COLOR),
        Box("basket_right", pos=(bx, by - iy / 2 - WALL / 2, h), size=(ix, WALL, WALL_H), color=BASKET_COLOR),
    ]


OBJECTS = [*BOXES, *TAGS, *_basket()]

# -- scoring ------------------------------------------------------------------------------------------------------


def in_basket(state) -> bool:
    """The item's centre is inside the basket's walls, below their tops."""
    x, y, z = (float(v) for v in state.pos)
    return abs(x - BASKET_XY[0]) < BASKET_IN[0] / 2 and abs(y - BASKET_XY[1]) < BASKET_IN[1] / 2 and z < FLOOR + WALL_H


def basket(objects) -> set[str]:
    return {n for n in ITEMS if in_basket(objects[f"item_{n}"])}


def outcome(objects) -> str:
    """'exact' (the 3 and the 7), 'half' (only one of them), 'empty', or 'wrong' (anything else in the basket)."""
    b = basket(objects)
    if b == SOLUTION:
        return "exact"
    if not b:
        return "empty"
    return "half" if b < SOLUTION else "wrong"


def success(objects):
    """The basket holds exactly the items whose prices add up to 10, all still."""
    return outcome(objects) == "exact" and all(objects[f"item_{n}"].resting() for n in SOLUTION)


def distance(objects):
    """Euros between the basket's total and the budget."""
    return float(abs(BUDGET - sum(ITEMS[n][1] for n in basket(objects))))


def score(objects):
    """1.0 for exactly the 3 and the 7; 0 otherwise. No partial credit: putting in one random item would hit the 3
    or the 7 half the time, so a half score would reward guessing."""
    return 1.0 if outcome(objects) == "exact" else 0.0


def demo():
    """The arms take turns: the left arm puts the green item (3) in the basket's left half and moves aside while the
    right arm waits at its ready pose; then the right arm puts the orange item (7) in the right half. Each grip
    pauses 2.5 s above the item and lets go with its bottom 1.5 cm above the basket walls."""
    travel_z = TOP + 0.20
    grip_z = TOP + ITEM[2] / 2
    drop_z = FLOOR + WALL_H + 0.015 + ITEM[2] / 2

    def into(name: str, dy: float):
        place = (BASKET_XY[0], BASKET_XY[1] + dy, drop_z)
        plan = pick_place_waypoints((ITEM_X, ITEMS[name][0], grip_z), place, travel_z=travel_z)
        hover = plan[0]
        return [hover, Waypoint(2.5, hover.pos, FINGER_OPEN, "wait", hover.yaw), *plan[1:]]

    left = into("green", 0.05) + [Waypoint(1.5, (0.18, 0.28, travel_z), FINGER_OPEN, "out of the way", 0.0)]
    left_time = sum(w.duration for w in left)
    right_ready = (0.318, -0.298, TOP + 0.257)
    right = [Waypoint(left_time, right_ready, FINGER_OPEN, "wait for the left arm", 0.0), *into("orange", -0.05)]
    right.append(Waypoint(1.5, (0.18, -0.25, travel_z), FINGER_OPEN, "out of the way", 0.0))
    return {"left": left, "right": right}
