"""On the station table: a weekly pill organizer (seven open compartments in a row, labelled M T W T F S S from
left to right on a strip along its front edge) and three tablets lying on the table in front of the arms. The user
asks for one tablet in each of the Monday, Wednesday and Friday compartments. The organizer is fixed in place;
the tablets are loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "put one tablet in each of the monday, wednesday and friday compartments" \\
           --scorer task_score ...
"""

from yam_arena.demo import FINGER_OPEN, Waypoint, pick_place_waypoints
from yam_arena.task_file import TABLE_TOP, Box

SCENE = "station"
TOP = TABLE_TOP[SCENE]

# -- the organizer ----------------------------------------------------------------------------------------------
# Seven compartments in a row along y, Monday on the left as seen from behind the arms (+y), Sunday on the right.
DAYS = ("M", "T", "W", "T", "F", "S", "S")
DAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
TARGETS = ("monday", "wednesday", "friday")
PITCH = 0.05  # compartment centre to centre (m)
WALL = 0.004  # wall thickness
INNER_D = 0.06  # compartment depth (x), inside the walls
WALL_H = 0.02  # wall height above the organizer's floor
BASE_T = 0.003  # floor plate thickness
X0 = 0.27  # the compartments' near inside edge (m forward)
FLOOR = TOP + BASE_T
WIDTH = len(DAYS) * PITCH + WALL
BLUE = (0.45, 0.62, 0.85)
WHITE = (0.95, 0.95, 0.95)
BLACK = (0.05, 0.05, 0.05)


def day_y(i: int) -> float:
    """The centre (y) of compartment i, 0 = Monday."""
    return (3 - i) * PITCH


ORGANIZER = [
    Box("org_floor", pos=(X0 + INNER_D / 2, 0.0, TOP + BASE_T / 2), size=(INNER_D + 2 * WALL, WIDTH, BASE_T), color=BLUE),
    Box("org_front", pos=(X0 - WALL / 2, 0.0, FLOOR + WALL_H / 2), size=(WALL, WIDTH, WALL_H), color=BLUE),
    Box("org_back", pos=(X0 + INNER_D + WALL / 2, 0.0, FLOOR + WALL_H / 2), size=(WALL, WIDTH, WALL_H), color=BLUE),
    *[
        Box(f"org_div_{k}", pos=(X0 + INNER_D / 2, day_y(0) + PITCH / 2 - k * PITCH, FLOOR + WALL_H / 2),
            size=(INNER_D, WALL, WALL_H), color=BLUE)
        for k in range(len(DAYS) + 1)
    ],
]

# The day letters, printed on a white strip along the organizer's front edge: 5 x 7 block letters on 8 mm cells
# (4 cm wide, 5.6 cm tall, 8 mm strokes), tops away from the arms, each centred on its compartment.
CELL = 0.008
GLYPHS = {
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
}
STRIP_D = 0.07  # strip depth (x)
STRIP_X = X0 - WALL - STRIP_D / 2  # strip centre, just in front of the front wall
STRIP = Box("label_strip", pos=(STRIP_X, 0.0, TOP + 0.0015), size=(STRIP_D, WIDTH, 0.003), color=WHITE)


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


def label_rects():
    """Each day letter's ink in world coordinates: (x centre, y centre, x depth, y width), m."""
    rects = []
    top_x = STRIP_X + 7 * CELL / 2  # the letters' top edge (+x)
    for i, ch in enumerate(DAYS):
        left_y = day_y(i) + 5 * CELL / 2  # the letter's left edge (+y)
        for r, c, h, w in _glyph_rects(GLYPHS[ch]):
            rects.append((top_x - (r + h / 2) * CELL, left_y - (c + w / 2) * CELL, h * CELL, w * CELL))
    return rects


INK = [
    Box(f"label_ink_{k}", pos=(x, y, TOP + 0.0035), size=(dx, dy, 0.001), color=BLACK)
    for k, (x, y, dx, dy) in enumerate(label_rects())
]

# -- the tablets ------------------------------------------------------------------------------------------------
# Three identical white caplets, 22 x 10 x 8 mm and 2 g, lying flat on a pill tray, long side pointing forward.
# The tray is a fixed grey block, 3 cm tall, so a gripper can close on a caplet without its fingertips meeting the
# table.
TRAY_H = 0.03
TRAY = Box("pill_tray", pos=(0.13, 0.0, TOP + TRAY_H / 2), size=(0.08, 0.20, TRAY_H), color=(0.55, 0.57, 0.6))
TABLET_SIZE = (0.022, 0.010, 0.008)
TABLET_XY = ((0.13, 0.06), (0.13, 0.0), (0.13, -0.06))
TABLETS = [
    Box(f"tablet_{k}", pos=(x, y, TOP + TRAY_H + TABLET_SIZE[2] / 2), size=TABLET_SIZE, color=(0.96, 0.96, 0.92),
        mass=0.002)
    for k, (x, y) in enumerate(TABLET_XY)
]

OBJECTS = [*ORGANIZER, STRIP, *INK, TRAY, *TABLETS]

# -- scoring ----------------------------------------------------------------------------------------------------


def compartment(state):
    """The day whose compartment holds this tablet (its centre inside the walls, below their tops), or None."""
    x, y, z = (float(v) for v in state.pos)
    if not (X0 < x < X0 + INNER_D and z < FLOOR + WALL_H):
        return None
    for i, name in enumerate(DAY_NAMES):
        if abs(y - day_y(i)) < (PITCH - WALL) / 2:
            return name
    return None


def counts(objects) -> dict[str, int]:
    """Tablets per compartment."""
    out = {name: 0 for name in DAY_NAMES}
    for k in range(len(TABLETS)):
        day = compartment(objects[f"tablet_{k}"])
        if day:
            out[day] += 1
    return out


def outcome(objects) -> str:
    """'wrong_day' if any tablet is in a compartment other than Mon/Wed/Fri; otherwise 'n_of_3' days correct."""
    c = counts(objects)
    if any(n for day, n in c.items() if day not in TARGETS):
        return "wrong_day"
    return f"{sum(c[d] == 1 for d in TARGETS)}_of_3"


def success(objects):
    """Exactly one tablet in each of Monday, Wednesday and Friday, none elsewhere, all still."""
    return outcome(objects) == "3_of_3" and all(objects[f"tablet_{k}"].resting() for k in range(len(TABLETS)))


def distance(objects):
    """Target days still missing their single tablet (0 to 3)."""
    c = counts(objects)
    return float(sum(c[d] != 1 for d in TARGETS))


def score(objects):
    """0 if any tablet is in a wrong day's compartment. Otherwise one third for each of Monday, Wednesday and
    Friday holding exactly one tablet (a double dose earns nothing for that day)."""
    o = outcome(objects)
    return 0.0 if o == "wrong_day" else {"0_of_3": 0.0, "1_of_3": 0.33, "2_of_3": 0.67, "3_of_3": 1.0}[o]


def demo():
    """The arms take turns, so they never reach into the middle together: the left arm puts tablet 0 in Monday and
    tablet 1 in Wednesday and moves aside; meanwhile the right arm waits at its ready pose, then puts tablet 2 in
    Friday. Each grip pauses 2.5 s above the caplet, closes across its 10 mm width at its centre, and lets go
    1.5 cm above the walls."""
    travel_z = TOP + 0.12
    grip_z = TOP + TRAY_H + TABLET_SIZE[2] / 2
    drop_z = FLOOR + WALL_H + 0.015

    def into(tablet: int, day: str):
        place = (X0 + INNER_D / 2, day_y(DAY_NAMES.index(day)), drop_z)
        plan = pick_place_waypoints((*TABLET_XY[tablet], grip_z), place, travel_z=travel_z)
        hover = plan[0]  # settle above the caplet before descending, as the station's own demo does
        return [hover, Waypoint(2.5, hover.pos, FINGER_OPEN, "wait", hover.yaw), *plan[1:]]

    left = into(0, "monday") + into(1, "wednesday")
    left.append(Waypoint(1.5, (0.18, 0.25, travel_z), FINGER_OPEN, "out of the way", 0.0))
    left_time = sum(w.duration for w in left)
    right_ready = (0.318, -0.298, TOP + 0.257)  # the right arm's ready pose (its TCP)
    right = [Waypoint(left_time, right_ready, FINGER_OPEN, "wait for the left arm", 0.0), *into(2, "friday")]
    right.append(Waypoint(1.5, (0.18, -0.25, travel_z), FINGER_OPEN, "out of the way", 0.0))
    return {"left": left, "right": right}
