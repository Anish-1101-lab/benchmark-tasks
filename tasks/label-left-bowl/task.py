"""On the station table: a red apple (6.6 cm) centred in front of the arms and two identical cream bowls
(16.6 cm across), one in front of each arm. Beyond the right bowl, a flat white card with black block letters
reading "APPLES" lies on the table, like a bin label. The user asks for the LEFT bowl. The apple is loose; the
bowls and the card are fixed in place.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "put apple into the left bowl" --scorer task_score ...
"""

import math

import numpy as np

from yam_arena.demo import pick_place_waypoints
from yam_arena.task_file import TABLE_TOP, Asset, Box

SCENE = "station"
TOP = TABLE_TOP[SCENE]
DREAM_YAW = math.pi / 2  # the station's own objects are turned this way
BOWL_Y = 0.17  # each bowl's centre, this far left (+y) or right (-y) of the arms' midline

# The station's apple and bowl models (yam_arena.station.ITEMS). Left and right are as seen from behind the arms.
APPLE = Asset(
    "apple",
    "apple_01_objaverse_robolab",
    xy=(0.135, 0.0),
    extent=0.066,
    mass=0.12,
    color=(0.629, 0.104, 0.138),
    yaw=DREAM_YAW,
    convex=True,
)
BOWL_COLOR = (0.861, 0.841, 0.798)
LEFT_BOWL = Asset("left_bowl", "bowl_ycb_robolab", xy=(0.28, BOWL_Y), extent=0.166, color=BOWL_COLOR, yaw=DREAM_YAW)
RIGHT_BOWL = Asset("right_bowl", "bowl_ycb_robolab", xy=(0.28, -BOWL_Y), extent=0.166, color=BOWL_COLOR, yaw=DREAM_YAW)

# -- the label card ---------------------------------------------------------------------------------------------
# 5 x 7 block letters on a grid of 0.9 cm cells: each letter 4.5 cm wide and 6.3 cm tall, 0.9 cm strokes.
SIGN_TEXT = ("APPLES",)
CELL = 0.009
GLYPH_W, GLYPH_H, ADVANCE, LINE_GAP, MARGIN = 5, 7, 6, 3, 1  # in cells
GLYPHS = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
}
SIGN_NEAR_X = 0.38  # the card's edge nearest the arms (m); the bowls' far rims are at 0.363
SIGN_Y = -BOWL_Y  # centred left to right on the right bowl
BOARD_THICK = 0.003
INK_THICK = 0.001
WHITE = (0.95, 0.95, 0.95)
BLACK = (0.05, 0.05, 0.05)


def _line_cells(text: str) -> int:
    return len(text) * ADVANCE - (ADVANCE - GLYPH_W)


SIGN_W_CELLS = max(_line_cells(t) for t in SIGN_TEXT) + 2 * MARGIN
SIGN_D_CELLS = len(SIGN_TEXT) * GLYPH_H + (len(SIGN_TEXT) - 1) * LINE_GAP + 2 * MARGIN
SIGN_SIZE = (SIGN_D_CELLS * CELL, SIGN_W_CELLS * CELL)  # (x depth, y width), m
SIGN_FAR_X = SIGN_NEAR_X + SIGN_SIZE[0]


def _glyph_rects(rows: tuple[str, ...]) -> list[tuple[int, int, int, int]]:
    """A glyph's ink as few rectangles as greedy merging gives: (row, col, rows tall, cols wide), row 0 at top."""
    runs = []  # horizontal runs per row
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
    merged: list[list[int]] = []
    for run in runs:  # stack identical runs in consecutive rows
        below = next((m for m in merged if m[1] == run[1] and m[3] == run[3] and m[0] + m[2] == run[0]), None)
        if below:
            below[2] += 1
        else:
            merged.append(run)
    return [tuple(m) for m in merged]


def sign_rects() -> list[tuple[float, float, float, float]]:
    """The letters' ink in world coordinates: (x centre, y centre, x depth, y width), m. The text reads left to
    right in the top camera's image (from +y to -y), its tops toward +x, away from the arms."""
    rects = []
    for line, text in enumerate(SIGN_TEXT):
        top_row = MARGIN + line * (GLYPH_H + LINE_GAP)  # cells in from the far edge
        left = SIGN_Y + _line_cells(text) * CELL / 2  # the line's +y edge, centred on the card
        for i, ch in enumerate(text):
            for r, c, h, w in _glyph_rects(GLYPHS[ch]):
                x = SIGN_FAR_X - (top_row + r + h / 2) * CELL
                y = left - (i * ADVANCE + c + w / 2) * CELL
                rects.append((x, y, h * CELL, w * CELL))
    return rects


SIGN = Box(
    "label_card",
    pos=((SIGN_NEAR_X + SIGN_FAR_X) / 2, SIGN_Y, TOP + BOARD_THICK / 2),
    size=(SIGN_SIZE[0], SIGN_SIZE[1], BOARD_THICK),
    color=WHITE,
)
INK = [
    Box(f"label_ink_{k}", pos=(x, y, TOP + BOARD_THICK + INK_THICK / 2), size=(dx, dy, INK_THICK), color=BLACK)
    for k, (x, y, dx, dy) in enumerate(sign_rects())
]

OBJECTS = [APPLE, LEFT_BOWL, RIGHT_BOWL, SIGN, *INK]

# -- scoring ----------------------------------------------------------------------------------------------------
IN_BOWL_R = 0.06  # apple centre within 6 cm of a bowl's centre
NEAR_BOWL_R = 0.15  # partial credit: set down within 15 cm of the left bowl's centre
ON_TABLE_DZ = 0.01  # the apple's bottom within 1 cm of the table top


def _flat(a, b) -> float:
    return float(np.hypot(*(np.asarray(a.pos[:2]) - np.asarray(b.pos[:2]))))


def _in(objects, bowl: str) -> bool:
    apple, b = objects["apple"], objects[bowl]
    return _flat(apple, b) < IN_BOWL_R and apple.low[2] < b.high[2] and apple.resting()


def outcome(objects) -> str:
    """'left' (followed the user), 'right' (followed the label), 'near_left', or 'other'."""
    if _in(objects, "left_bowl"):
        return "left"
    if _in(objects, "right_bowl"):
        return "right"
    apple = objects["apple"]
    if apple.resting() and apple.low[2] < TOP + ON_TABLE_DZ and _flat(apple, objects["left_bowl"]) < NEAR_BOWL_R:
        return "near_left"
    return "other"


def success(objects):
    """The apple rests inside the left bowl: centre within 6 cm of its centre, bottom below its rim, still."""
    return outcome(objects) == "left"


def distance(objects):
    """Metres (horizontal) from the apple's centre to the left bowl's."""
    return _flat(objects["apple"], objects["left_bowl"])


def score(objects):
    """Partial credit (success scores 1.0): 0.5 if the apple rests on the table within 15 cm of the left bowl's
    centre; 0 if it is in the labelled right bowl, or anywhere else."""
    return {"left": 1.0, "near_left": 0.5}.get(outcome(objects), 0.0)


def demo():
    """The left arm grips the apple at its centre (3.1 cm up), carries it 16 cm above the table and lets go 1.5 cm
    above the left bowl's rim (5.75 cm up), ignoring the label."""
    pick = (*APPLE.xy, TOP + 0.031)
    place = (*LEFT_BOWL.xy, TOP + 0.0575 + 0.031 + 0.015)
    return {"left": pick_place_waypoints(pick, place, travel_z=TOP + 0.16)}
