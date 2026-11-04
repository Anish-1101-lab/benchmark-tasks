"""Write the sign as a full-size SVG for printing, from the same layout task.py builds in simulation.

    python make_sign.py sign.svg

Runs without Isaac Sim or yam_arena: it only needs task.py's sign layout, so it stands in for the two
yam_arena modules task.py imports when they are missing.
"""

import importlib.util
import sys
import types
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _stub_yam_arena() -> None:
    try:
        import yam_arena.task_file  # noqa: F401

        return
    except ImportError:
        pass

    @dataclass(frozen=True)
    class Shape:
        name: str
        pos: tuple = (0.0, 0.0, 0.0)
        size: tuple = (0.0, 0.0, 0.0)
        color: tuple = (0.7, 0.7, 0.7)
        mass: float | None = None

    @dataclass(frozen=True)
    class Asset:
        name: str
        asset: str
        xy: tuple
        extent: float
        mass: float | None = None
        color: tuple | None = None
        yaw: float = 0.0
        convex: bool = False

    task_file = types.ModuleType("yam_arena.task_file")
    task_file.TABLE_TOP = {"station": 0.7475, "tabletop": 0.75}
    task_file.Box, task_file.Asset = Shape, Asset
    demo = types.ModuleType("yam_arena.demo")
    demo.pick_place_waypoints = lambda *a, **k: []
    sys.modules.update({"yam_arena": types.ModuleType("yam_arena"), "yam_arena.task_file": task_file,
                        "yam_arena.demo": demo})


def load_task():
    _stub_yam_arena()
    spec = importlib.util.spec_from_file_location("ignore_sign_task", HERE / "task.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def svg(task) -> str:
    """The sign as seen from the arms' side: SVG x runs from the sign's +y edge to its -y edge, SVG y from its far
    (+x) edge to its near edge. Units are millimetres, so it prints at full size."""
    depth, width = (round(v * 1000, 1) for v in task.SIGN_SIZE)
    half_w = task.SIGN_SIZE[1] / 2
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}mm" height="{depth}mm" '
        f'viewBox="0 0 {width} {depth}">',
        f'<rect x="0" y="0" width="{width}" height="{depth}" fill="#ffffff"/>',
    ]
    for x, y, dx, dy in task.sign_rects():
        left = (half_w - (y + dy / 2)) * 1000
        top = (task.SIGN_FAR_X - (x + dx / 2)) * 1000
        parts.append(
            f'<rect x="{left:.1f}" y="{top:.1f}" width="{dy * 1000:.1f}" height="{dx * 1000:.1f}" fill="#000000"/>'
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "sign.svg")
    out.write_text(svg(load_task()))
    print(f"wrote {out}")
