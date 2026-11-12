"""lidkit: a fixed base with several lids, each on its own friction hinge, as one object in a yam_arena task file.

Adapted from ``tasks/laptop-under-stack/hingekit.py`` in this repository (one lid on a free base). Changes: any
number of lids, one revolute joint each; a snap latch on each lid; optionally the base is welded to the world
(``weld=True``, no ``mass``), otherwise it is a free body of ``mass`` that seeded resets move like any other free
object; the state reports every lid's angle.

yam_arena task files only hold rigid primitives. Importing this module hooks ``yam_arena.scene`` (and the
embodiment's reset and step) without modifying yam_arena, so a task file can list a :class:`Lidded` object.

Each hinge is a constant-torque (Coulomb) friction hinge: it holds its lid at any angle and gives way only to a
torque above ``hold_torque``. A stiff position drive whose force is capped at ``hold_torque`` holds the lid, and
after every control step its target is dragged along behind the lid, never more than ``hold_torque / STIFFNESS``
away (a spring-slider): the lid sticks until pushed with more than ``hold_torque``, then slides against it.

The snap latch: within ``latch_deg`` of closed, a constant ``latch_torque`` pulls the lid shut (a feed-forward joint
effort, on top of the friction). A latched lid only opens when lifted with more than ``latch_torque +
hold_torque``, and a lid pressed down into the last ``latch_deg`` snaps shut by itself.

``success()`` and ``score()`` receive a :class:`LidState` for the object: the base body's pose, velocities and
world-aligned bounds, and ``angles``, every hinge angle in radians (0 closed, positive open), in lid order.

Pure Python at import time; everything that needs Isaac Sim is imported lazily.
"""

from __future__ import annotations

import importlib.abc
import importlib.util
import math
import sys
from dataclasses import dataclass

import numpy as np
from yam_arena.task_file import Box, ObjectState

Color = tuple[float, float, float]
BoxSpec = tuple[tuple[float, float, float], tuple[float, float, float], Color]  # centre, size (m), sRGB
LidSpec = tuple[tuple[float, float, float], tuple[BoxSpec, ...]]  # hinge point (base frame), boxes (lid frame)

STIFFNESS = 20.0  # N m/rad
DAMPING = 0.05  # N m s/rad


@dataclass(frozen=True)
class Lidded(Box):
    """A base welded to the world, with lids on friction hinges. ``pos`` is the base body's origin (world, m);
    ``base_boxes`` are in the base frame. Each lid is (hinge point in the base frame, boxes in the lid frame); the
    hinge axis is the base's +y, the lid frame's origin is on the hinge and equals the base frame when closed. A lid
    opens by turning about +y, so it should reach out along -x. Subclasses Box only so yam_arena's task-file checks
    accept it."""

    base_boxes: tuple[BoxSpec, ...] = ()
    lids: tuple[LidSpec, ...] = ()
    weld: bool = False  # weld the base to the world where it spawns (then leave ``mass`` None)
    base_mass: float = 0.3  # kg, the welded base's mass (a free base uses ``mass``)
    lid_mass: float = 0.005  # kg, each
    hold_torque: float = 0.02  # N m: each hinge's friction torque
    upper_deg: float = 150.0  # each hinge's open stop
    latch_deg: float = 4.0  # the snap latch acts below this angle
    latch_torque: float = 0.08  # N m pulling a lid shut inside the latch zone
    yaw_jitter_deg: float = 0.0  # a free base moved by a seeded reset is also turned by up to this much (see below)
    friction: float = 0.6

    def _check(self) -> None:
        if not self.name.isidentifier():
            raise ValueError(f"object name {self.name!r} must be a Python identifier")
        if not (self.base_boxes and self.lids):
            raise ValueError(f"{self.name}: a Lidded object needs base boxes and at least one lid")
        if self.weld != (self.mass is None):
            raise ValueError(f"{self.name}: a welded base takes base_mass and no mass; a free base needs a mass")
        if not (self.base_mass > 0 and self.lid_mass > 0 and self.hold_torque > 0 and self.latch_torque >= 0):
            raise ValueError(f"{self.name}: masses and torques must be positive")
        if not 0 < self.upper_deg <= 180:
            raise ValueError(f"{self.name}: upper_deg must be in (0, 180]")


@dataclass(frozen=True)
class LidState(ObjectState):
    angles: tuple[float, ...] = ()  # rad, 0 closed, in lid order


def joint_name(spec: Lidded, i: int) -> str:
    return f"{spec.name}_lid_{i}"


# -- building the articulation (Isaac Sim only) ---------------------------------------------------------------

_SPECS: dict[str, Lidded] = {}


def _spawn(prim_path: str, cfg, translation=None, orientation=None, **kwargs):
    import isaaclab.sim as sim_utils
    from isaaclab.sim.utils import bind_physics_material, bind_visual_material
    from isaaclab.sim.utils.stage import get_current_stage
    from pxr import Gf, PhysxSchema, Sdf, UsdGeom, UsdPhysics

    from yam_arena.station import linear_rgb

    spec = _SPECS[cfg.part]
    stage = get_current_stage()
    root = UsdGeom.Xform.Define(stage, prim_path)
    root.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*(translation or (0, 0, 0))))
    x, y, z, w = orientation if orientation is not None else (0.0, 0.0, 0.0, 1.0)
    root.AddOrientOp(precision=UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(w, x, y, z))
    material = f"{prim_path}/Looks/physics"
    pm = sim_utils.RigidBodyMaterialCfg(static_friction=spec.friction, dynamic_friction=spec.friction)
    pm.func(material, pm)
    looks: dict[Color, str] = {}

    def body(path, pos, mass, boxes):
        xf = UsdGeom.Xform.Define(stage, path)
        xf.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*pos))
        xf.AddOrientOp(precision=UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(1, 0, 0, 0))
        prim = xf.GetPrim()
        UsdPhysics.RigidBodyAPI.Apply(prim)
        UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(mass)
        rb = PhysxSchema.PhysxRigidBodyAPI.Apply(prim)
        rb.CreateMaxDepenetrationVelocityAttr(1.0)
        for i, (centre, size, color) in enumerate(boxes):
            cube = UsdGeom.Cube.Define(stage, f"{path}/box_{i}")
            cube.CreateSizeAttr(1.0)
            cube.AddTranslateOp().Set(Gf.Vec3d(*centre))
            cube.AddScaleOp().Set(Gf.Vec3f(*size))
            box = cube.GetPrim()
            UsdPhysics.CollisionAPI.Apply(box)
            cp = PhysxSchema.PhysxCollisionAPI.Apply(box)
            cp.CreateContactOffsetAttr(0.002)
            cp.CreateRestOffsetAttr(0.0)
            bind_physics_material(str(box.GetPath()), material, stage=stage)
            if color not in looks:
                looks[color] = f"{prim_path}/Looks/c{len(looks)}"
                vis = sim_utils.PreviewSurfaceCfg(diffuse_color=linear_rgb(color), roughness=0.5)
                vis.func(looks[color], vis)
            bind_visual_material(str(box.GetPath()), looks[color], stage=stage)
        return prim

    base_path = f"{prim_path}/base"
    base = body(base_path, (0.0, 0.0, 0.0), spec.base_mass if spec.weld else spec.mass, spec.base_boxes)
    for i, (hinge, boxes) in enumerate(spec.lids):
        lid_path = f"{prim_path}/lid_{i}"
        body(lid_path, hinge, spec.lid_mass, boxes)
        j = UsdPhysics.RevoluteJoint.Define(stage, f"{prim_path}/{joint_name(spec, i)}")
        j.CreateAxisAttr("Y")
        j.CreateBody0Rel().SetTargets([Sdf.Path(base_path)])
        j.CreateBody1Rel().SetTargets([Sdf.Path(lid_path)])
        j.CreateLocalPos0Attr(Gf.Vec3f(*hinge))
        j.CreateLocalRot0Attr(Gf.Quatf(1, 0, 0, 0))
        j.CreateLocalPos1Attr(Gf.Vec3f(0, 0, 0))
        j.CreateLocalRot1Attr(Gf.Quatf(1, 0, 0, 0))
        j.CreateLowerLimitAttr(0.0)  # USD revolute limits are in degrees
        j.CreateUpperLimitAttr(spec.upper_deg)
        drive = UsdPhysics.DriveAPI.Apply(j.GetPrim(), "angular")  # USD angular gains are per degree
        drive.CreateTypeAttr("force")
        drive.CreateStiffnessAttr(STIFFNESS * math.pi / 180)
        drive.CreateDampingAttr(DAMPING * math.pi / 180)
        drive.CreateMaxForceAttr(spec.hold_torque)
        drive.CreateTargetPositionAttr(0.0)
    if spec.weld:  # weld the base to the world where it was spawned
        fix = UsdPhysics.FixedJoint.Define(stage, f"{prim_path}/anchor")
        fix.CreateBody1Rel().SetTargets([Sdf.Path(base_path)])
        world = UsdGeom.Xformable(base).ComputeLocalToWorldTransform(0)
        t, q = world.ExtractTranslation(), world.ExtractRotationQuat()
        fix.CreateLocalPos0Attr(Gf.Vec3f(*t))
        fix.CreateLocalRot0Attr(Gf.Quatf(q.GetReal(), *q.GetImaginary()))
        fix.CreateLocalPos1Attr(Gf.Vec3f(0, 0, 0))
        fix.CreateLocalRot1Attr(Gf.Quatf(1, 0, 0, 0))
    UsdPhysics.ArticulationRootAPI.Apply(base)
    art = PhysxSchema.PhysxArticulationAPI.Apply(base)
    art.CreateEnabledSelfCollisionsAttr(False)
    art.CreateSolverPositionIterationCountAttr(32)
    art.CreateSolverVelocityIterationCountAttr(4)
    return root.GetPrim()


def _arena_object(spec: Lidded):
    from isaaclab.actuators import ImplicitActuatorCfg
    from isaaclab.assets import ArticulationCfg
    from isaaclab.sim.spawners.spawner_cfg import SpawnerCfg
    from isaaclab.sim.utils import clone
    from isaaclab.utils import configclass
    from isaaclab_arena.assets.object import Object
    from isaaclab_arena.assets.object_type import ObjectType
    from isaaclab_arena.utils.pose import Pose

    @configclass
    class LiddedSpawnerCfg(SpawnerCfg):
        func: object = clone(_spawn)
        part: str = ""

    class LiddedObject(Object):
        def _generate_articulation_cfg(self):
            hinges = ImplicitActuatorCfg(
                joint_names_expr=[f"{spec.name}_lid_.*"],
                stiffness=STIFFNESS,
                damping=DAMPING,
                joint_effort_limit=spec.hold_torque,
            )
            cfg = ArticulationCfg(prim_path=self.prim_path, spawn=self.spawner_cfg, actuators={"hinges": hinges})
            return self._add_initial_pose_to_cfg(cfg)

    return LiddedObject(
        name=spec.name,
        object_type=ObjectType.ARTICULATION,
        spawner_cfg=LiddedSpawnerCfg(part=spec.name),
        initial_pose=Pose(position_xyz=tuple(spec.pos), rotation_xyzw=(0, 0, math.sin(spec.yaw / 2), math.cos(spec.yaw / 2))),
    )


def _t(x):
    return getattr(x, "torch", x)


def _np(x) -> np.ndarray:
    return _t(x).detach().cpu().numpy().astype(np.float64)


def _state(environment, spec: Lidded) -> LidState:
    base = environment.unwrapped
    asset = base.scene[spec.name]
    pose = _np(asset.data.root_link_pose_w)[0]
    pos = pose[:3] - _np(base.scene.env_origins)[0]
    vel = next((_np(getattr(asset.data, k))[0] for k in ("root_link_vel_w", "root_vel_w") if hasattr(asset.data, k)), np.zeros(6))
    q = _np(asset.data.joint_pos)[0]
    names = list(asset.joint_names)
    angles = tuple(float(q[names.index(joint_name(spec, i))]) for i in range(len(spec.lids)))
    return LidState(pos, pose[3:7], vel[:3], vel[3:6], pos, pos, angles)


_TARGET: dict = {}


def _set_targets(environment, zero: bool = False) -> None:
    """Spring-slider friction on every hinge (see the module docstring)."""
    if environment is None:
        return
    scene = environment.unwrapped.scene
    for spec in _SPECS.values():
        asset = scene[spec.name]
        q = _t(asset.data.joint_pos).clone()
        target = _TARGET.get(spec.name)
        if zero or target is None:
            target = q * 0
        else:
            lim = spec.hold_torque / STIFFNESS
            target = q + (target - q).clamp(-lim, lim)
        _TARGET[spec.name] = target
        latched = q < math.radians(spec.latch_deg)
        effort = latched.float() * -spec.latch_torque if hasattr(latched, "float") else latched * -spec.latch_torque
        command = getattr(getattr(asset, "actuators", None), "target_command", None)
        if command is not None:  # Isaac Lab 3.0, as yam_arena.actions uses it
            command.set_position_index(value=target)
            command.set_effort_index(value=effort)
        else:
            asset.set_joint_position_target(target)
            asset.set_joint_effort_target(effort)


# -- hooking yam_arena ----------------------------------------------------------------------------------------


def _turn_bases(environment) -> bool:
    """Turn each free base with ``yaw_jitter_deg`` that a seeded reset has moved off its spawn spot by a yaw drawn
    from that offset (so it is fixed by the run's seed, like the offset itself), about the base's origin. A base
    still on its spawn spot (``-E object_jitter=0``) is left square. Returns whether any base was turned."""
    turned = False
    scene = environment.unwrapped.scene
    for spec in _SPECS.values():
        if spec.weld or spec.yaw_jitter_deg <= 0:
            continue
        asset = scene[spec.name]
        pose = _t(asset.data.root_link_pose_w).clone()
        offset = _np(pose)[0][:2] - _np(scene.env_origins)[0][:2] - np.asarray(spec.pos[:2])
        if np.abs(offset).max() < 1e-4:
            continue
        seed = int(round(abs(offset[0]) * 1e6)) * 1_000_003 + int(round(abs(offset[1]) * 1e6))
        yaw = math.radians(np.random.default_rng(seed).uniform(-spec.yaw_jitter_deg, spec.yaw_jitter_deg))
        pose[:, 3:7] = pose[:, 3:7] * 0
        pose[:, 5] = math.sin(yaw / 2)  # (x, y, z, w): a turn about the vertical only
        pose[:, 6] = math.cos(yaw / 2)
        asset.write_root_pose_to_sim_index(root_pose=pose)
        asset.write_root_velocity_to_sim_index(root_velocity=_t(asset.data.default_root_vel).clone() * 0)
        turned = True
    return turned


def _patch_scene(scene) -> None:
    if getattr(scene, "_lidkit", False):
        return
    task_object, object_states = scene.task_object, scene.object_states

    def patched_task_object(spec):
        if isinstance(spec, Lidded):
            _SPECS[spec.name] = spec
            return _arena_object(spec)
        return task_object(spec)

    def patched_object_states(environment, names):
        plain = [n for n in names if n not in _SPECS]
        out = object_states(environment, plain) if plain else {}
        out.update({n: _state(environment, _SPECS[n]) for n in names if n in _SPECS})
        return {n: out[n] for n in names}

    scene.task_object, scene.object_states = patched_task_object, patched_object_states
    scene._lidkit = True


def _patch_embodiment(module) -> None:
    cls = module.YamArenaEmbodiment
    if getattr(cls, "_lidkit", False):
        return
    task_step, reset = cls._task_step, cls.reset

    def patched_task_step(self, *a, **k):
        _set_targets(self._env)
        return task_step(self, *a, **k)

    def patched_reset(self, *a, **k):
        _set_targets(getattr(self, "_env", None), zero=True)  # so every lid settles closed
        obs = reset(self, *a, **k)
        _set_targets(self._env, zero=True)
        if _turn_bases(self._env):
            for _ in range(max(1, round(1.0 / self._base.step_dt))):  # settle again, as yam_arena's reset does
                self._env.step(self._ready)
            for _ in range(4):
                self._base.sim.render()
            obs = self._observation()
        return obs

    cls._task_step, cls.reset = patched_task_step, patched_reset
    cls._lidkit = True


class _Finder(importlib.abc.MetaPathFinder):
    """Patches each target module right after it is first imported (yam_arena.scene needs Isaac Sim running)."""

    targets = {"yam_arena.scene": _patch_scene, "yam_arena.inspect_embodiment": _patch_embodiment}

    def find_spec(self, fullname, path, target=None):
        if fullname not in self.targets:
            return None
        sys.meta_path.remove(self)
        try:
            spec = importlib.util.find_spec(fullname)
        finally:
            sys.meta_path.insert(0, self)
        if spec is None or spec.loader is None:
            return None
        exec_module, patch = spec.loader.exec_module, self.targets[fullname]

        def patched_exec(module):
            exec_module(module)
            patch(module)

        spec.loader.exec_module = patched_exec
        return spec


def install() -> None:
    for name, patch in _Finder.targets.items():
        if name in sys.modules:
            patch(sys.modules[name])
    if not any(isinstance(f, _Finder) for f in sys.meta_path):
        sys.meta_path.insert(0, _Finder())


install()
