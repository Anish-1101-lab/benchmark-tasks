"""On the station table: three open sorting chutes (bins) labelled A, B and C, three small parcels wrapped in red,
blue and green, and a printed routing card that gives each colour's chute: RED -> C, BLUE -> A, GREEN -> B. The
user asks for each parcel to go into the chute the card lists for its colour. The mapping is arbitrary on purpose,
so the robot has to read the card rather than match colours. The chutes and the card are fixed; the parcels are
loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "sort each parcel into the chute that the routing card lists for its colour" \\
           --scorer task_score ...
"""

from yam_arena.demo import FINGER_OPEN, Waypoint, pick_place_waypoints
from yam_arena.task_file import TABLE_TOP, Box

SCENE = "station"
TOP = TABLE_TOP[SCENE]
WHITE = (0.95, 0.95, 0.95)
BLACK = (0.05, 0.05, 0.05)

# -- block letters ----------------------------------------------------------------------------------------------
GLYPHS = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
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


def letter(name: str, ch: str, centre_xy, cell: float, z: float) -> list[Box]:
    """A 5 x 7 block letter lying flat, centred on ``centre_xy``, its top toward +x (readable from the arms)."""
    cx, cy = centre_xy
    top_x, left_y = cx + 7 * cell / 2, cy + 5 * cell / 2
    return [
        Box(f"{name}_{k}", pos=(top_x - (r + h / 2) * cell, left_y - (c + w / 2) * cell, z), size=(h * cell, w * cell, 0.001),
            color=BLACK)
        for k, (r, c, h, w) in enumerate(_glyph_rects(GLYPHS[ch]))
    ]


# -- the chutes -------------------------------------------------------------------------------------------------
# Three open bins in a row along y: A on the left (as seen from behind the arms), B in the middle, C on the right.
CHUTES = {"A": 0.15, "B": 0.0, "C": -0.15}  # centre y of each bin (m)
BIN_X0 = 0.32  # near inside edge (m forward)
BIN_D, BIN_W = 0.10, 0.12  # inside depth (x) and width (y)
WALL, WALL_H, BASE_T = 0.004, 0.06, 0.003
FLOOR = TOP + BASE_T
GREY = (0.62, 0.64, 0.67)


def _bin(ch: str, y: float) -> list[Box]:
    xc, h = BIN_X0 + BIN_D / 2, FLOOR + WALL_H / 2
    out_d, out_w = BIN_D + 2 * WALL, BIN_W + 2 * WALL
    return [
        Box(f"bin{ch}_floor", pos=(xc, y, TOP + BASE_T / 2), size=(out_d, out_w, BASE_T), color=GREY),
        Box(f"bin{ch}_front", pos=(BIN_X0 - WALL / 2, y, h), size=(WALL, out_w, WALL_H), color=GREY),
        Box(f"bin{ch}_back", pos=(BIN_X0 + BIN_D + WALL / 2, y, h), size=(WALL, out_w, WALL_H), color=GREY),
        Box(f"bin{ch}_left", pos=(xc, y + BIN_W / 2 + WALL / 2, h), size=(BIN_D, WALL, WALL_H), color=GREY),
        Box(f"bin{ch}_right", pos=(xc, y - BIN_W / 2 - WALL / 2, h), size=(BIN_D, WALL, WALL_H), color=GREY),
    ]


# Each chute's letter on a white tag lying flat just in front of it: 3.5 x 4.9 cm letters (7 mm cells).
TAG_CELL = 0.007
TAG_D = 0.055
TAG_X = BIN_X0 - WALL - TAG_D / 2 - 0.002
CHUTE_PARTS = []
for ch, y in CHUTES.items():
    CHUTE_PARTS += _bin(ch, y)
    CHUTE_PARTS.append(Box(f"tag{ch}", pos=(TAG_X, y, TOP + 0.0015), size=(TAG_D, 0.06, 0.003), color=WHITE))
    CHUTE_PARTS += letter(f"tag{ch}_ink", ch, (TAG_X, y), TAG_CELL, TOP + 0.0035)

# -- the routing card -------------------------------------------------------------------------------------------
# A white card lying flat on the right of the table with three rows, far to near: a colour swatch and that colour's
# chute letter (3 x 4.2 cm, 6 mm cells).
COLOURS = {"red": (0.80, 0.12, 0.12), "blue": (0.15, 0.32, 0.80), "green": (0.12, 0.60, 0.22)}
ROUTE = {"red": "C", "blue": "A", "green": "B"}
CARD_CELL = 0.006
CARD_X = (0.05, 0.23)  # near and far edges
CARD_Y = (-0.27, -0.13)  # right and left edges
ROW_X = {"red": 0.20, "blue": 0.14, "green": 0.08}  # each row's centre
SWATCH_Y, LETTER_Y = -0.165, -0.235
CARD = [
    Box("card", pos=(sum(CARD_X) / 2, sum(CARD_Y) / 2, TOP + 0.0015),
        size=(CARD_X[1] - CARD_X[0], CARD_Y[1] - CARD_Y[0], 0.003), color=WHITE),
]
for colour, x in ROW_X.items():
    CARD.append(Box(f"swatch_{colour}", pos=(x, SWATCH_Y, TOP + 0.0035), size=(0.04, 0.04, 0.001), color=COLOURS[colour]))
    CARD += letter(f"card_{colour}", ROUTE[colour], (x, LETTER_Y), CARD_CELL, TOP + 0.0035)

# -- the parcels ------------------------------------------------------------------------------------------------
# Three 5 cm cardboard cubes, 120 g, wrapped in coloured paper, in a queue on the arms' midline.
PARCEL = 0.05
PARCEL_X = {"red": 0.07, "blue": 0.15, "green": 0.23}
PARCELS = [
    Box(f"parcel_{c}", pos=(x, 0.0, TOP + PARCEL / 2), size=(PARCEL, PARCEL, PARCEL), color=COLOURS[c], mass=0.12)
    for c, x in PARCEL_X.items()
]

OBJECTS = [*CHUTE_PARTS, *CARD, *PARCELS]

# -- scoring ----------------------------------------------------------------------------------------------------


def chute_of(state):
    """The chute holding this parcel (its centre inside the bin's walls, below their tops), or None."""
    x, y, z = (float(v) for v in state.pos)
    if not (BIN_X0 < x < BIN_X0 + BIN_D and z < FLOOR + WALL_H):
        return None
    return next((ch for ch, cy in CHUTES.items() if abs(y - cy) < BIN_W / 2), None)


def placements(objects) -> dict[str, str | None]:
    return {c: chute_of(objects[f"parcel_{c}"]) for c in COLOURS}


def outcome(objects) -> str:
    """'missort' if any parcel is in a wrong chute; otherwise 'n_of_3' parcels in their own chute."""
    p = placements(objects)
    if any(ch is not None and ch != ROUTE[c] for c, ch in p.items()):
        return "missort"
    return f"{sum(ch == ROUTE[c] for c, ch in p.items())}_of_3"


def success(objects):
    """Every parcel rests in the chute the card lists for its colour."""
    return outcome(objects) == "3_of_3" and all(objects[f"parcel_{c}"].resting() for c in COLOURS)


def distance(objects):
    """Parcels not yet in their own chute (0 to 3)."""
    p = placements(objects)
    return float(sum(ch != ROUTE[c] for c, ch in p.items()))


def score(objects):
    """0 if any parcel is in a wrong chute; otherwise one third per parcel in its own chute."""
    o = outcome(objects)
    return 0.0 if o == "missort" else {"0_of_3": 0.0, "1_of_3": 0.33, "2_of_3": 0.67, "3_of_3": 1.0}[o]


def demo():
    """The arms take turns, so they never reach into the middle together: the left arm puts blue in A and green in
    B and moves aside while the right arm waits at its ready pose; then the right arm puts red in C. Each grip
    pauses 2.5 s above the parcel, closes across it at mid-height, and lets go with the parcel's bottom 1.5 cm above
    the chute walls."""
    travel_z = TOP + 0.16
    grip_z = TOP + PARCEL / 2
    drop_z = FLOOR + WALL_H + 0.015 + PARCEL / 2

    def into(colour: str):
        place = (BIN_X0 + BIN_D / 2, CHUTES[ROUTE[colour]], drop_z)
        plan = pick_place_waypoints((PARCEL_X[colour], 0.0, grip_z), place, travel_z=travel_z)
        hover = plan[0]
        return [hover, Waypoint(2.5, hover.pos, FINGER_OPEN, "wait", hover.yaw), *plan[1:]]

    left = into("blue") + into("green")
    left.append(Waypoint(1.5, (0.18, 0.25, travel_z), FINGER_OPEN, "out of the way", 0.0))
    left_time = sum(w.duration for w in left)
    right_ready = (0.318, -0.298, TOP + 0.257)  # the right arm's ready pose (its TCP)
    right = [Waypoint(left_time, right_ready, FINGER_OPEN, "wait for the left arm", 0.0), *into("red")]
    right.append(Waypoint(1.5, (0.18, -0.25, travel_z), FINGER_OPEN, "out of the way", 0.0))
    return {"left": left, "right": right}
