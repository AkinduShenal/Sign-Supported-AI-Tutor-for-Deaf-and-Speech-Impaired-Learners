"""Generate reusable mathematics sign clips for the Louise tutor avatar.

The signs are approximate animations based on the supplied Sri Lankan Math
Sign Language reference. The script keeps the original Blender source intact,
writes an editable animated copy, and exports the compressed GLB used by the
frontend.

Run from the repository root:

    /Applications/Blender.app/Contents/MacOS/Blender \
      -b avatar/louise_tutor.blend \
      --python avatar/create_sign_animations.py
"""

from __future__ import annotations

import math
import shutil
import tempfile
from pathlib import Path
from typing import TypedDict

import bpy
from mathutils import Matrix, Quaternion, Vector


ROOT = Path(bpy.path.abspath("//")).parent
OUTPUT_BLEND = ROOT / "avatar" / "louise_tutor_with_signs.blend"
OUTPUT_GLB = ROOT / "frontend" / "public" / "models" / "louise_tutor.glb"

ARMATURE_NAME = "Armature"
PREFIX = "mixamorig8:"
FPS = 30
START_FRAME = 1
END_FRAME = 72
NEUTRAL_SETTLE_FRAME = 9
EXIT_SETTLE_OFFSET = 9

FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")


class HandState(TypedDict):
    wrist: tuple[float, float, float]
    pole: tuple[float, float, float]
    direction: tuple[float, float, float]
    palm: tuple[float, float, float]
    extended: set[str]


class PoseState(TypedDict):
    Left: HandState
    Right: HandState


def hand_state(
    wrist: tuple[float, float, float],
    pole: tuple[float, float, float],
    direction: tuple[float, float, float],
    palm: tuple[float, float, float],
    extended: set[str],
) -> HandState:
    return {
        "wrist": wrist,
        "pole": pole,
        "direction": direction,
        "palm": palm,
        "extended": extended,
    }


def neutral_state() -> PoseState:
    """A relaxed, symmetrical pose that avoids the previous bent-arm idle."""
    return {
        "Left": hand_state(
            (0.31, -0.015, 0.76),
            (0.40, -0.10, 0.96),
            (0.0, 0.0, -1.0),
            (-1.0, 0.0, 0.0),
            set(FINGERS),
        ),
        "Right": hand_state(
            (-0.31, -0.015, 0.76),
            (-0.40, -0.10, 0.96),
            (0.0, 0.0, -1.0),
            (1.0, 0.0, 0.0),
            set(FINGERS),
        ),
    }


def create_target(name: str) -> bpy.types.Object:
    target = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(target)
    target.empty_display_type = "PLAIN_AXES"
    target.empty_display_size = 0.06
    target.hide_render = True
    return target


def orientation_from_y_z(y_axis: Vector, preferred_z: Vector) -> Matrix:
    y_axis = y_axis.normalized()
    z_axis = preferred_z - y_axis * preferred_z.dot(y_axis)
    if z_axis.length < 0.001:
        z_axis = Vector((0.0, -1.0, 0.0))
    z_axis.normalize()
    x_axis = y_axis.cross(z_axis).normalized()
    z_axis = x_axis.cross(y_axis).normalized()
    return Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()


def keyframe_orientation(
    target: bpy.types.Object,
    frame: int,
    direction: tuple[float, float, float],
    palm: tuple[float, float, float],
) -> None:
    target.rotation_mode = "QUATERNION"
    target.rotation_quaternion = orientation_from_y_z(
        Vector(direction), Vector(palm)
    ).to_quaternion()
    target.keyframe_insert(data_path="rotation_quaternion", frame=frame)


def signed_angle(vector_u: Vector, vector_v: Vector, normal: Vector) -> float:
    """Return a signed angle around the supplied normal."""
    if vector_u.length < 1e-8 or vector_v.length < 1e-8 or normal.length < 1e-8:
        return 0.0

    u = vector_u.normalized()
    v = vector_v.normalized()
    n = normal.normalized()

    angle = u.angle(v)
    if u.cross(v).dot(n) < 0.0:
        angle = -angle
    return angle


def calculate_pole_angle(
    armature: bpy.types.Object,
    side: str,
    pole_world_location: Vector,
) -> float:
    """Calculate the IK pole angle from Louise's real bone roll.

    This replaces the old hard-coded -90/+90 degree values. Mixamo-style
    left/right arm bones do not necessarily have mirrored local roll, so fixed
    values can make symmetric targets produce asymmetric elbows.
    """
    base_bone = armature.pose.bones[f"{PREFIX}{side}Arm"]
    ik_bone = armature.pose.bones[f"{PREFIX}{side}ForeArm"]

    pole_location = armature.matrix_world.inverted() @ pole_world_location

    chain_axis = ik_bone.tail - base_bone.head
    upper_axis = base_bone.tail - base_bone.head

    pole_normal = chain_axis.cross(pole_location - base_bone.head)
    if pole_normal.length < 1e-8:
        return 0.0

    projected_pole_axis = pole_normal.cross(upper_axis)
    if projected_pole_axis.length < 1e-8:
        return 0.0

    return signed_angle(
        base_bone.x_axis,
        projected_pole_axis,
        upper_axis,
    )


def add_constraints(
    armature: bpy.types.Object,
    side: str,
    wrist_target: bpy.types.Object,
    pole_target: bpy.types.Object,
    orientation_target: bpy.types.Object,
    pole_reference: tuple[float, float, float],
    action_name: str,
) -> None:
    forearm = armature.pose.bones[f"{PREFIX}{side}ForeArm"]
    hand = armature.pose.bones[f"{PREFIX}{side}Hand"]

    pole_target.location = pole_reference
    bpy.context.view_layer.update()

    ik = forearm.constraints.new("IK")
    ik.target = wrist_target
    ik.pole_target = pole_target
    ik.chain_count = 2
    ik.use_tail = True

    pole_angle = calculate_pole_angle(
        armature,
        side,
        pole_target.matrix_world.translation,
    )
    ik.pole_angle = pole_angle

    print(
        f"[{action_name}] {side} pole angle: "
        f"{math.degrees(pole_angle):.2f} degrees"
    )

    copy_rotation = hand.constraints.new("COPY_ROTATION")
    copy_rotation.target = orientation_target
    copy_rotation.owner_space = "WORLD"
    copy_rotation.target_space = "WORLD"
    copy_rotation.mix_mode = "REPLACE"


def keyframe_hand_shape(
    armature: bpy.types.Object,
    frame: int,
    side: str,
    extended: set[str],
) -> None:
    for finger in ("Index", "Middle", "Ring", "Pinky"):
        angles = (0.0, 0.0, 0.0)
        if finger not in extended:
            angles = tuple(math.radians(value) for value in (72, 88, 58))

        for joint, angle in zip((1, 2, 3), angles):
            bone = armature.pose.bones[f"{PREFIX}{side}Hand{finger}{joint}"]
            bone.rotation_mode = "QUATERNION"
            bone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0), angle)
            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)

    thumb_angles = (0.0, 0.0, 0.0)
    if "Thumb" not in extended:
        thumb_angles = tuple(math.radians(value) for value in (28, 48, 30))

    for joint, angle in zip((1, 2, 3), thumb_angles):
        bone = armature.pose.bones[f"{PREFIX}{side}HandThumb{joint}"]
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0), angle)
        bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)


def keyframe_pose(
    armature: bpy.types.Object,
    targets: dict[str, bpy.types.Object],
    frame: int,
    state: PoseState,
) -> None:
    for side in ("Left", "Right"):
        hand = state[side]
        wrist_target = targets[f"{side}_wrist"]
        pole_target = targets[f"{side}_pole"]
        orientation_target = targets[f"{side}_orientation"]

        wrist_target.location = hand["wrist"]
        wrist_target.keyframe_insert(data_path="location", frame=frame)

        pole_target.location = hand["pole"]
        pole_target.keyframe_insert(data_path="location", frame=frame)

        keyframe_orientation(
            orientation_target,
            frame,
            hand["direction"],
            hand["palm"],
        )
        keyframe_hand_shape(armature, frame, side, hand["extended"])


def smooth_action_curves(action: bpy.types.Action) -> None:
    """Smooth baked animation curves in legacy and Blender 5.x Actions."""
    legacy_fcurves = getattr(action, "fcurves", None)
    if legacy_fcurves is not None:
        for fcurve in legacy_fcurves:
            for point in fcurve.keyframe_points:
                point.interpolation = "BEZIER"
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"
        return

    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            channelbags = getattr(strip, "channelbags", None)
            if channelbags is None:
                continue

            for channelbag in channelbags:
                for fcurve in channelbag.fcurves:
                    for point in fcurve.keyframe_points:
                        point.interpolation = "BEZIER"
                        point.handle_left_type = "AUTO_CLAMPED"
                        point.handle_right_type = "AUTO_CLAMPED"


def create_action(
    armature: bpy.types.Object,
    name: str,
    sign_keyframes: list[tuple[int, PoseState]],
    frame_end: int = END_FRAME,
) -> bpy.types.Action:
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.transforms_clear()

    for bone in armature.pose.bones:
        for constraint in list(bone.constraints):
            bone.constraints.remove(constraint)

    action = bpy.data.actions.new(name)
    armature.animation_data_create()
    armature.animation_data.action = action

    targets: dict[str, bpy.types.Object] = {}
    for side in ("Left", "Right"):
        for role in ("wrist", "pole", "orientation"):
            targets[f"{side}_{role}"] = create_target(f"_{name}_{side}_{role}")

        calibration_state = sign_keyframes[0][1][side]

        add_constraints(
            armature,
            side,
            targets[f"{side}_wrist"],
            targets[f"{side}_pole"],
            targets[f"{side}_orientation"],
            calibration_state["pole"],
            name,
        )

    neutral = neutral_state()

    for frame in (START_FRAME, NEUTRAL_SETTLE_FRAME):
        keyframe_pose(armature, targets, frame, neutral)

    for frame, state in sign_keyframes:
        keyframe_pose(armature, targets, frame, state)

    for frame in (frame_end - EXIT_SETTLE_OFFSET, frame_end):
        keyframe_pose(armature, targets, frame, neutral)

    scene = bpy.context.scene
    scene.frame_set(START_FRAME)

    bpy.ops.nla.bake(
        frame_start=START_FRAME,
        frame_end=frame_end,
        step=1,
        only_selected=True,
        visual_keying=True,
        clear_constraints=True,
        clear_parents=False,
        use_current_action=True,
        clean_curves=True,
        bake_types={"POSE"},
    )

    bpy.ops.object.mode_set(mode="OBJECT")

    for target in targets.values():
        bpy.data.objects.remove(target, do_unlink=True)

    smooth_action_curves(action)

    action.name = name
    action.use_fake_user = True
    armature.animation_data.action = None
    return action


def addition_pose() -> PoseState:
    return {
        "Left": hand_state(
            (0.25, -0.20, 1.38),
            (0.55, -0.05, 1.23),
            (-1.0, 0.0, 0.0),
            (0.0, -1.0, 0.0),
            {"Index"},
        ),
        "Right": hand_state(
            (0.055, -0.22, 1.19),
            (-0.43, -0.06, 1.22),
            (0.0, 0.0, 1.0),
            (0.0, -1.0, 0.0),
            {"Index"},
        ),
    }


def subtraction_pose(right_height: float) -> PoseState:
    """Natural subtraction pose with lower shoulders and outward elbows.

    The wrists stay separated in front of the torso while the pole targets sit
    slightly outside each shoulder line. This prevents the elbows collapsing
    inward toward the body.
    """
    lifted_right = 1.12 + max(0.0, right_height - 1.30) * 0.45

    return {
        "Left": hand_state(
            (0.20, -0.34, 1.10),
            (0.62, -0.10, 1.00),
            (-1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0),
            set(FINGERS),
        ),
        "Right": hand_state(
            (-0.22, -0.30, lifted_right),
            (-0.62, -0.10, 1.00),
            (0.0, 0.0, -1.0),
            (0.0, -1.0, 0.0),
            set(),
        ),
    }


def equation_pose(outward: bool) -> PoseState:
    """Relaxed equation pose with low shoulders and outward elbow bend."""
    x = 0.32 if outward else 0.24

    return {
        "Left": hand_state(
            (x, -0.34, 1.11),
            (0.62, -0.10, 1.00),
            (-1.0, 0.0, 0.0),
            (0.0, -1.0, 0.0),
            {"Index", "Middle"},
        ),
        "Right": hand_state(
            (-x, -0.34, 1.11),
            (-0.62, -0.10, 1.00),
            (1.0, 0.0, 0.0),
            (0.0, -1.0, 0.0),
            {"Index", "Middle"},
        ),
    }


def balance_pose(offset: float) -> PoseState:
    """Relaxed balance pose with wider, outward-bending elbows."""
    return {
        "Left": hand_state(
            (0.29, -0.33, 1.09 + offset),
            (0.62, -0.10, 1.00),
            (-1.0, 0.0, 0.0),
            (0.0, -1.0, 0.0),
            set(FINGERS),
        ),
        "Right": hand_state(
            (-0.29, -0.33, 1.09 - offset),
            (-0.62, -0.10, 1.00),
            (1.0, 0.0, 0.0),
            (0.0, -1.0, 0.0),
            {"Index", "Middle"},
        ),
    }


def algebra_pose(stage: int) -> PoseState:
    if stage == 1:
        return {
            "Left": hand_state(
                (0.25, -0.20, 1.33),
                (0.53, -0.04, 1.18),
                (0.0, 0.0, 1.0),
                (0.0, -1.0, 0.0),
                set(FINGERS),
            ),
            "Right": hand_state(
                (-0.18, -0.22, 1.31),
                (-0.50, -0.04, 1.18),
                (1.0, 0.0, 0.0),
                (0.0, -1.0, 0.0),
                {"Index"},
            ),
        }

    return {
        "Left": hand_state(
            (0.08, -0.20, 1.24),
            (0.50, -0.03, 1.14),
            (-1.0, 0.0, 0.0),
            (0.0, -1.0, 0.0),
            set(),
        ),
        "Right": hand_state(
            (
                -0.06 + (0.08 if stage == 3 else 0.0),
                -0.22,
                1.29 + (0.07 if stage == 3 else 0.0),
            ),
            (-0.48, -0.03, 1.18),
            (1.0, 0.0, 0.0),
            (0.0, -1.0, 0.0),
            set(),
        ),
    }


def substitution_pose(distance: float) -> PoseState:
    return {
        "Left": hand_state(
            (distance, -0.18, 1.13),
            (0.30, -0.30, 1.30),
            (-1.0, 0.0, 0.0),
            (0.0, -1.0, 0.0),
            {"Index", "Middle", "Ring", "Pinky"},
        ),
        "Right": hand_state(
            (-distance, -0.18, 1.13),
            (-0.30, 0.00, 0.90),
            (1.0, 0.0, 0.0),
            (0.0, -1.0, 0.0),
            {"Index", "Middle", "Ring", "Pinky"},
        ),
    }


def number_pose(left_extended: set[str], right_extended: set[str]) -> PoseState:
    left_is_used = bool(left_extended)
    left = neutral_state()["Left"]

    if left_is_used:
        left = hand_state(
            (0.28, -0.18, 1.24),
            (0.54, -0.03, 1.16),
            (0.0, 0.0, 1.0),
            (0.0, -1.0, 0.0),
            left_extended,
        )

    return {
        "Left": left,
        "Right": hand_state(
            (-0.28, -0.18, 1.24),
            (-0.54, -0.03, 1.16),
            (0.0, 0.0, 1.0),
            (0.0, -1.0, 0.0),
            right_extended,
        ),
    }


def generate_actions(armature: bpy.types.Object) -> None:
    for old_action in list(bpy.data.actions):
        bpy.data.actions.remove(old_action)

    create_action(
        armature,
        "IDLE",
        [(18, neutral_state()), (22, neutral_state())],
        30,
    )

    create_action(
        armature,
        "ADDITION",
        [(25, addition_pose()), (47, addition_pose())],
    )

    create_action(
        armature,
        "SUBTRACTION",
        [
            (20, subtraction_pose(1.48)),
            (34, subtraction_pose(1.30)),
            (47, subtraction_pose(1.30)),
        ],
    )

    create_action(
        armature,
        "EQUATION",
        [
            (22, equation_pose(False)),
            (36, equation_pose(True)),
            (48, equation_pose(True)),
        ],
    )

    create_action(
        armature,
        "BALANCE",
        [
            (22, balance_pose(0.03)),
            (34, balance_pose(-0.03)),
            (47, balance_pose(0.0)),
        ],
    )

    create_action(
        armature,
        "ALGEBRA",
        [
            (20, algebra_pose(1)),
            (34, algebra_pose(2)),
            (47, algebra_pose(3)),
        ],
    )

    create_action(
        armature,
        "SUBSTITUTION",
        [
            (22, substitution_pose(0.30)),
            (38, substitution_pose(0.18)),
            (48, substitution_pose(0.18)),
        ],
    )

    create_action(
        armature,
        "NUMBER_3",
        [
            (24, number_pose(set(), {"Index", "Middle", "Ring"})),
            (48, number_pose(set(), {"Index", "Middle", "Ring"})),
        ],
    )

    create_action(
        armature,
        "NUMBER_4",
        [
            (24, number_pose(set(), {"Index", "Middle", "Ring", "Pinky"})),
            (48, number_pose(set(), {"Index", "Middle", "Ring", "Pinky"})),
        ],
    )

    create_action(
        armature,
        "NUMBER_5",
        [
            (24, number_pose(set(), set(FINGERS))),
            (48, number_pose(set(), set(FINGERS))),
        ],
    )

    create_action(
        armature,
        "NUMBER_7",
        [
            (24, number_pose(set(FINGERS), {"Index", "Middle"})),
            (48, number_pose(set(FINGERS), {"Index", "Middle"})),
        ],
    )

    for helper_action in list(bpy.data.actions):
        if helper_action.name.startswith("_"):
            bpy.data.actions.remove(helper_action)


def prepare_web_textures() -> Path:
    texture_dir = Path(tempfile.mkdtemp(prefix="louise_web_textures_"))

    for image in bpy.data.images:
        if image.source != "FILE" or not image.has_data:
            continue

        if image.packed_file is not None:
            image.unpack(method="REMOVE")

        width, height = image.size
        longest_side = max(width, height)

        if longest_side > 1024:
            scale = 1024 / longest_side
            image.scale(round(width * scale), round(height * scale))

        texture_path = texture_dir / image.name
        image.filepath_raw = str(texture_path)
        image.file_format = "PNG"
        image.save()
        image.filepath_raw = str(texture_path)

    return texture_dir


def main() -> None:
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = START_FRAME
    scene.frame_end = END_FRAME

    armature = bpy.data.objects.get(ARMATURE_NAME)

    if armature is None or armature.type != "ARMATURE":
        raise RuntimeError(f"Expected an armature named {ARMATURE_NAME!r}")

    generate_actions(armature)
    scene.frame_set(START_FRAME)

    OUTPUT_BLEND.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_GLB.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.save_as_mainfile(
        filepath=str(OUTPUT_BLEND),
        check_existing=False,
    )

    texture_dir = prepare_web_textures()

    try:
        for obj in bpy.context.selected_objects:
            obj.select_set(False)

        for obj in scene.objects:
            if obj.type in {"ARMATURE", "MESH"}:
                obj.select_set(True)

        bpy.context.view_layer.objects.active = armature

        bpy.ops.export_scene.gltf(
            filepath=str(OUTPUT_GLB),
            export_format="GLB",
            use_selection=True,
            export_animations=True,
            export_animation_mode="ACTIONS",
            export_bake_animation=False,
            export_optimize_animation_size=True,
            export_skins=True,
            export_morph=True,
            export_materials="EXPORT",
            export_image_format="JPEG",
            export_image_quality=85,
            export_jpeg_quality=85,
            export_texcoords=True,
            export_normals=True,
            export_tangents=False,
            export_yup=True,
            export_apply=False,
            export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=6,
        )
    finally:
        shutil.rmtree(texture_dir, ignore_errors=True)

    print(
        "Created actions:",
        sorted(action.name for action in bpy.data.actions),
    )
    print(f"Editable Blender output: {OUTPUT_BLEND}")
    print(f"Web GLB output: {OUTPUT_GLB}")


if __name__ == "__main__":
    main()
