"""On the station table: a mobile robot's chassis (a yellow block with an open battery bay on top) holding a
depleted battery pack, and a charging dock holding a charged pack of the same kind. The user asks for the swap: the
charged pack goes into the robot, the depleted one onto the charging plate. The plate is occupied, so the charged pack has
to come off before the depleted one can go on. The chassis and dock are fixed; the packs are loose.

Run it:  inspect-robots run --embodiment yam_arena -E task=task.py \\
           --instruction "swap the robot's depleted battery for the charged one on the charger, and leave the
           depleted one charging" --scorer task_score ...
"""

from yam_arena.demo import FINGER_CLOSED, FINGER_OPEN, Waypoint
from yam_arena.task_file import TABLE_TOP, Box

SCENE = "station"
TOP = TABLE_TOP[SCENE]

# -- battery packs ----------------------------------------------------------------------------------------------
PACK = (0.12, 0.05, 0.10)  # x (long side, forward), y (grip width), z (height), m
PACK_MASS = 0.15
PACK_COLOR = (0.13, 0.14, 0.16)
CLEAR = 0.008  # gap around a pack in its bay or dock, each side
INNER = (PACK[0] + 2 * CLEAR, PACK[1] + 2 * CLEAR)

# -- the robot chassis: a fixed yellow block whose top has an open battery bay ----------------------------------
BAY_XY = (0.20, 0.0)
BAY_FLOOR = TOP + 0.04  # the bay floor's height
CHASSIS_TOP = TOP + 0.08  # the chassis top (bay walls 4 cm tall)
CHASSIS = (0.18, 0.14)  # outer footprint, x and y
YELLOW = (0.93, 0.72, 0.12)


def _chassis() -> list[Box]:
    (bx, by), (cx_len, cy_len), (ix, iy) = BAY_XY, CHASSIS, INNER
    wall_h, wall_z = CHASSIS_TOP - BAY_FLOOR, (CHASSIS_TOP + BAY_FLOOR) / 2
    end_x = (cx_len - ix) / 2  # chassis length in front of and behind the bay
    side_y = (cy_len - iy) / 2
    return [
        Box("chassis_base", pos=(bx, by, (TOP + BAY_FLOOR) / 2), size=(cx_len, cy_len, BAY_FLOOR - TOP), color=YELLOW),
        Box("chassis_front", pos=(bx - ix / 2 - end_x / 2, by, wall_z), size=(end_x, cy_len, wall_h), color=YELLOW),
        Box("chassis_back", pos=(bx + ix / 2 + end_x / 2, by, wall_z), size=(end_x, cy_len, wall_h), color=YELLOW),
        Box("chassis_left", pos=(bx, by + iy / 2 + side_y / 2, wall_z), size=(ix, side_y, wall_h), color=YELLOW),
        Box("chassis_right", pos=(bx, by - iy / 2 - side_y / 2, wall_z), size=(ix, side_y, wall_h), color=YELLOW),
    ]


# -- the charging dock: a fixed flat charging plate with a green charging light ----------------------------------
# A pack charges when it stands on the plate with its centre within 2.5 cm of the plate's centre (the plate's
# contact area); there are no guide walls.
DOCK_XY = (0.38, 0.0)  # straight behind the robot, both on the arms' midline
DOCK_FLOOR = TOP + 0.005
DOCK_PLATE = (PACK[0] + 0.06, PACK[1] + 0.06)  # 18 x 11 cm
DOCK_GREY = (0.2, 0.2, 0.22)


def _dock() -> list[Box]:
    (dx, dy), (px, py) = DOCK_XY, DOCK_PLATE
    return [
        Box("dock_plate", pos=(dx, dy, (TOP + DOCK_FLOOR) / 2), size=(px, py, DOCK_FLOOR - TOP), color=DOCK_GREY),
        Box("dock_light", pos=(dx + px / 2 - 0.012, dy + py / 2 - 0.012, DOCK_FLOOR + 0.004), size=(0.012, 0.012, 0.008),
            color=(0.15, 0.85, 0.3)),
    ]


DEPLETED = Box("pack_depleted", pos=(*BAY_XY, BAY_FLOOR + PACK[2] / 2), size=PACK, color=PACK_COLOR, mass=PACK_MASS)
CHARGED = Box("pack_charged", pos=(*DOCK_XY, DOCK_FLOOR + PACK[2] / 2), size=PACK, color=PACK_COLOR, mass=PACK_MASS)

OBJECTS = [*_chassis(), *_dock(), DEPLETED, CHARGED]

# -- scoring ----------------------------------------------------------------------------------------------------
BAY_TOL = 0.01  # in the robot: the pack's centre within 1 cm (horizontally) of the bay's centre...
DOCK_TOL = 0.025  # on the charger: within 2.5 cm of the plate's centre...
SEAT_Z = 0.01  # ...and in both cases its bottom within 1 cm of the floor it stands on


def seated(state, holder_xy, floor_z, tol) -> bool:
    x, y = (float(v) for v in state.pos[:2])
    bottom = float(state.low[2])
    off = ((x - holder_xy[0]) ** 2 + (y - holder_xy[1]) ** 2) ** 0.5
    return off <= tol and abs(bottom - floor_z) <= SEAT_Z and state.resting()


def outcome(objects) -> str:
    """'swapped' (both done), 'robot_only' (charged pack in the robot), 'dock_only' (depleted pack on the charger),
    or 'neither'."""
    in_robot = seated(objects["pack_charged"], BAY_XY, BAY_FLOOR, BAY_TOL)
    charging = seated(objects["pack_depleted"], DOCK_XY, DOCK_FLOOR, DOCK_TOL)
    return {(True, True): "swapped", (True, False): "robot_only", (False, True): "dock_only"}.get(
        (in_robot, charging), "neither")


def success(objects):
    """The charged pack is seated in the robot's bay and the depleted pack is seated on the charger."""
    return outcome(objects) == "swapped"


def distance(objects):
    """Metres (horizontal) from the charged pack to the robot's bay."""
    x, y = (float(v) for v in objects["pack_charged"].pos[:2])
    return ((x - BAY_XY[0]) ** 2 + (y - BAY_XY[1]) ** 2) ** 0.5


def score(objects):
    """1.0 for the full swap; 0.5 if only one half is done (the charged pack seated in the robot, or the depleted
    pack seated on the charger); 0 otherwise."""
    return {"swapped": 1.0, "robot_only": 0.5, "dock_only": 0.5}.get(outcome(objects), 0.0)


# -- demo -------------------------------------------------------------------------------------------------------
GRIP_BELOW_TOP = 0.025  # the fingers close 2.5 cm below a pack's top
TRAVEL_Z = TOP + 0.19  # carry height: a held pack's bottom clears the chassis top by 3.5 cm
RIGHT_READY = (0.318, -0.298, TOP + 0.257)
LEFT_READY = (0.318, 0.298, TOP + 0.257)


def _tcp(xy, floor_z):
    """Where the TCP is when gripping a pack that stands on ``floor_z`` at ``xy``."""
    return (*xy, floor_z + PACK[2] - GRIP_BELOW_TOP)


def _seg(d, p, f, label):
    return Waypoint(d, p, f, label, 0.0)


def demo():
    """A bimanual hand-off. The right arm lifts the charged pack off the dock and holds it up out of the way; the
    left arm moves the depleted pack from the robot onto the now-empty dock and steps aside; then the right arm
    lowers the charged pack into the robot's bay."""
    up = lambda xy: (*xy, TRAVEL_Z)  # noqa: E731
    dock_grip, bay_grip = _tcp(DOCK_XY, DOCK_FLOOR), _tcp(BAY_XY, BAY_FLOOR)
    # Where each arm aims when placing. In the simulator the right arm's held pack hangs 2.2 cm right of the
    # commanded point above the bay (measured while hovering), so the demo aims 2.2 cm left there. Only the demo
    # needs this; the task and its scoring use the true positions. The left arm aims at the charging plate directly.
    dock_aim = DOCK_XY
    bay_aim = (BAY_XY[0], BAY_XY[1] + 0.022)
    dock_drop = (*dock_aim, dock_grip[2] + 0.005)
    bay_drop = (*bay_aim, bay_grip[2] + 0.005)
    park = (0.14, -0.26, TRAVEL_Z)  # where the right arm holds the charged pack meanwhile

    right_first = [
        _seg(1.5, up(DOCK_XY), FINGER_OPEN, "to the charged pack"),
        _seg(2.5, up(DOCK_XY), FINGER_OPEN, "wait"),
        _seg(1.5, dock_grip, FINGER_OPEN, "descend"),
        _seg(0.8, dock_grip, FINGER_CLOSED, "close"),
        _seg(1.5, up(DOCK_XY), FINGER_CLOSED, "lift off the dock"),
        _seg(1.5, park, FINGER_CLOSED, "hold it out of the way"),
    ]
    t_right_parked = sum(w.duration for w in right_first)

    left_plan = [
        _seg(t_right_parked, LEFT_READY, FINGER_OPEN, "wait for the dock to be clear"),
        _seg(1.5, up(BAY_XY), FINGER_OPEN, "to the depleted pack"),
        _seg(2.5, up(BAY_XY), FINGER_OPEN, "wait"),
        _seg(1.5, bay_grip, FINGER_OPEN, "descend"),
        _seg(0.8, bay_grip, FINGER_CLOSED, "close"),
        _seg(1.5, up(BAY_XY), FINGER_CLOSED, "lift out of the bay"),
        _seg(1.8, up(dock_aim), FINGER_CLOSED, "carry to the dock"),
        _seg(2.0, up(dock_aim), FINGER_CLOSED, "settle above the dock"),
        _seg(1.5, dock_drop, FINGER_CLOSED, "lower onto the dock"),
        _seg(0.6, dock_drop, FINGER_OPEN, "release"),
        _seg(1.0, up(dock_aim), FINGER_OPEN, "retreat"),
        _seg(1.5, (0.16, 0.26, TRAVEL_Z), FINGER_OPEN, "out of the way"),
    ]
    t_left_done = sum(w.duration for w in left_plan)

    right_plan = right_first + [
        _seg(t_left_done - t_right_parked, park, FINGER_CLOSED, "hold while the left arm works"),
        _seg(2.0, up(bay_aim), FINGER_CLOSED, "carry to the robot"),
        _seg(2.0, up(bay_aim), FINGER_CLOSED, "settle above the bay"),
        _seg(1.5, bay_drop, FINGER_CLOSED, "lower into the bay"),
        _seg(0.6, bay_drop, FINGER_OPEN, "release"),
        _seg(1.0, up(bay_aim), FINGER_OPEN, "retreat"),
        _seg(1.5, (0.16, -0.26, TRAVEL_Z), FINGER_OPEN, "out of the way"),
    ]
    return {"left": left_plan, "right": right_plan}
