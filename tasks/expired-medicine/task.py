"""On the station table: three identical white medicine boxes standing in a line in front of the arms, each with
its expiry date (MM/YY) printed on a card beside it, and an open grey return bin on the left. The instruction gives
today's date (November 2026) and asks for every expired box in the return bin: 05/26 and 09/25 have expired, 02/27
has not. The cards and the bin are fixed; the boxes are loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "it is november 2026. put every expired medicine box in the return bin" --scorer task_score ...
"""

from yam_arena.demo import FINGER_OPEN, Waypoint, pick_place_waypoints
from yam_arena.task_file import TABLE_TOP, Box

SCENE = "station"
TOP = TABLE_TOP[SCENE]
WHITE = (0.95, 0.95, 0.95)
BLACK = (0.05, 0.05, 0.05)

# -- 5 x 7 block characters -------------------------------------------------------------------------------------
GLYPHS = {
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".##..", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
}
CELL, ADVANCE, MARGIN = 0.005, 6, 1  # 2.5 x 3.5 cm characters, one cell apart, one cell of margin


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


def card(name: str, text: str, centre_xy) -> list[Box]:
    """A white card lying flat with ``text`` printed on it in black, readable from behind the arms (tops toward +x,
    reading from +y to -y)."""
    cols = len(text) * ADVANCE - 1 + 2 * MARGIN
    rows = 7 + 2 * MARGIN
    cx, cy = centre_xy
    depth, width = rows * CELL, cols * CELL
    parts = [Box(name, pos=(cx, cy, TOP + 0.0015), size=(depth, width, 0.003), color=WHITE)]
    top_x, left_y = cx + depth / 2 - MARGIN * CELL, cy + width / 2 - MARGIN * CELL
    k = 0
    for i, ch in enumerate(text):
        for r, c, h, w in _glyph_rects(GLYPHS[ch]):
            x = top_x - (r + h / 2) * CELL
            y = left_y - (i * ADVANCE + c + w / 2) * CELL
            parts.append(Box(f"{name}_ink_{k}", pos=(x, y, TOP + 0.0035), size=(h * CELL, w * CELL, 0.001), color=BLACK))
            k += 1
    return parts


# -- the medicine boxes and their expiry cards ------------------------------------------------------------------
BOX = (0.05, 0.05, 0.08)  # x, y, height (m)
BOX_MASS = 0.06
BOX_X = {"a": 0.10, "b": 0.20, "c": 0.30}  # in a line on the arms' midline, near to far
EXPIRY = {"a": "05/26", "b": "02/27", "c": "09/25"}
EXPIRED = {"a", "c"}  # as of November 2026
CARD_Y = -0.11  # each card lies to the right of its box
BOXES = [
    Box(f"box_{k}", pos=(x, 0.0, TOP + BOX[2] / 2), size=BOX, color=(0.97, 0.97, 0.97), mass=BOX_MASS)
    for k, x in BOX_X.items()
]
CARDS = [part for k, x in BOX_X.items() for part in card(f"card_{k}", EXPIRY[k], (x, CARD_Y))]

# -- the return bin ---------------------------------------------------------------------------------------------
BIN_XY = (0.27, 0.20)
BIN_IN = 0.16  # inside, square
WALL, WALL_H, BASE_T = 0.004, 0.10, 0.003
FLOOR = TOP + BASE_T
GREY = (0.55, 0.57, 0.6)


def _bin() -> list[Box]:
    (bx, by), h, out = BIN_XY, FLOOR + WALL_H / 2, BIN_IN + 2 * WALL
    return [
        Box("bin_floor", pos=(bx, by, TOP + BASE_T / 2), size=(out, out, BASE_T), color=GREY),
        Box("bin_front", pos=(bx - BIN_IN / 2 - WALL / 2, by, h), size=(WALL, out, WALL_H), color=GREY),
        Box("bin_back", pos=(bx + BIN_IN / 2 + WALL / 2, by, h), size=(WALL, out, WALL_H), color=GREY),
        Box("bin_left", pos=(bx, by + BIN_IN / 2 + WALL / 2, h), size=(BIN_IN, WALL, WALL_H), color=GREY),
        Box("bin_right", pos=(bx, by - BIN_IN / 2 - WALL / 2, h), size=(BIN_IN, WALL, WALL_H), color=GREY),
    ]


OBJECTS = [*BOXES, *CARDS, *_bin()]

# -- scoring ----------------------------------------------------------------------------------------------------


def in_bin(state) -> bool:
    """The box's centre is inside the bin's walls, below their tops."""
    x, y, z = (float(v) for v in state.pos)
    return abs(x - BIN_XY[0]) < BIN_IN / 2 and abs(y - BIN_XY[1]) < BIN_IN / 2 and z < FLOOR + WALL_H


def outcome(objects) -> str:
    """'unexpired_returned' if the in-date box is in the bin; otherwise 'n_of_2' expired boxes in the bin."""
    if in_bin(objects["box_b"]):
        return "unexpired_returned"
    return f"{sum(in_bin(objects[f'box_{k}']) for k in EXPIRED)}_of_2"


def success(objects):
    """Both expired boxes rest in the bin and the in-date one doesn't."""
    return outcome(objects) == "2_of_2" and all(objects[f"box_{k}"].resting() for k in EXPIRED)


def distance(objects):
    """Expired boxes not yet in the bin (0 to 2)."""
    return float(sum(not in_bin(objects[f"box_{k}"]) for k in EXPIRED))


def score(objects):
    """0 if the in-date box is in the bin; otherwise 0.5 per expired box in the bin."""
    return {"unexpired_returned": 0.0, "0_of_2": 0.0, "1_of_2": 0.5, "2_of_2": 1.0}[outcome(objects)]


def demo():
    """The left arm puts box a (05/26) and then box c (09/25) in the bin, side by side, and leaves box b (02/27).
    Each grip pauses 2.5 s above the box, closes at mid-height, and lets go with the box's bottom 1.5 cm above the
    bin's walls."""
    travel_z = TOP + 0.22
    grip_z = TOP + BOX[2] / 2
    drop_z = FLOOR + WALL_H + 0.015 + BOX[2] / 2

    def into(k: str, dy: float):
        place = (BIN_XY[0], BIN_XY[1] + dy, drop_z)
        plan = pick_place_waypoints((BOX_X[k], 0.0, grip_z), place, travel_z=travel_z)
        hover = plan[0]
        return [hover, Waypoint(2.5, hover.pos, FINGER_OPEN, "wait", hover.yaw), *plan[1:]]

    left = into("a", -0.04) + into("c", 0.04)
    left.append(Waypoint(1.5, (0.18, 0.28, travel_z), FINGER_OPEN, "out of the way", 0.0))
    return {"left": left}
