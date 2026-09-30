"""Create an approximate Sinhala Sign Language ADDITION clip for Louise.

Run from the repository root:

    /Applications/Blender.app/Contents/MacOS/Blender \
      -b avatar/louise_tutor.blend \
      --python avatar/create_addition_animation.py

The source Blender file is left untouched. The script writes an editable
animated copy and replaces the web-ready GLB used by the tutor interface.
"""

from __future__ import annotations

import math
import shutil
import tempfile
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(bpy.path.abspath("//")).parent
OUTPUT_BLEND = ROOT / "avatar" / "louise_tutor_with_addition.blend"
OUTPUT_GLB = ROOT / "frontend" / "public" / "models" / "louise_tutor.glb"

ARMATURE_NAME = "Armature"
PREFIX = "mixamorig8:"
ACTION_NAME = "ADDITION"

FPS = 30
START_FRAME = 1
END_FRAME = 72


def world_to_object_location(obj: bpy.types.Object, location: tuple[float, float, float]) -> Vector:
    return obj.matrix_world.inverted() @ Vector(location)


def create_target(name: str, location: tuple[float, float, float]) -> bpy.types.Object:
    target = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(target)
    target.empty_display_type = "PLAIN_AXES"
    target.empty_display_size = 0.07
    target.location = location
    target.hide_render = True
    return target


def keyframe_location(
    target: bpy.types.Object,
    frame: int,
    location: tuple[float, float, float],
) -> None:
    target.location = location
    target.keyframe_insert(data_path="location", frame=frame)


def orientation_from_y_z(y_axis: Vector, preferred_z: Vector) -> Matrix:
    """Return a stable world rotation whose local Y follows the fingers."""
    y_axis = y_axis.normalized()
    z_axis = preferred_z - y_axis * preferred_z.dot(y_axis)
    if z_axis.length < 0.001:
        z_axis = Vector((0.0, -1.0, 0.0))
    z_axis.normalize()
    x_axis = y_axis.cross(z_axis).normalized()
    z_axis = x_axis.cross(y_axis).normalized()
    return Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()


def set_orientation(
    target: bpy.types.Object,
    frame: int,
    direction: tuple[float, float, float],
    palm_normal: tuple[float, float, float],
) -> None:
    rotation = orientation_from_y_z(Vector(direction), Vector(palm_normal))
    target.rotation_mode = "QUATERNION"
    target.rotation_quaternion = rotation.to_quaternion()
    target.keyframe_insert(data_path="rotation_quaternion", frame=frame)


def add_arm_constraints(
    armature: bpy.types.Object,
    side: str,
    wrist_target: bpy.types.Object,
    pole_target: bpy.types.Object,
    orientation_target: bpy.types.Object,
) -> None:
    forearm = armature.pose.bones[f"{PREFIX}{side}ForeArm"]
    hand = armature.pose.bones[f"{PREFIX}{side}Hand"]

    ik = forearm.constraints.new("IK")
    ik.name = f"{ACTION_NAME}_{side}_ARM_IK"
    ik.target = wrist_target
    ik.pole_target = pole_target
    ik.chain_count = 2
    ik.use_tail = True
    ik.pole_angle = math.radians(-90 if side == "Left" else 90)

    copy_rotation = hand.constraints.new("COPY_ROTATION")
    copy_rotation.name = f"{ACTION_NAME}_{side}_HAND_ORIENTATION"
    copy_rotation.target = orientation_target
    copy_rotation.owner_space = "WORLD"
    copy_rotation.target_space = "WORLD"
    copy_rotation.mix_mode = "REPLACE"


def keyframe_finger_curl(
    armature: bpy.types.Object,
    frame: int,
    amount: float,
) -> None:
    # Index fingers stay extended to form the visible plus shape.
    for side in ("Left", "Right"):
        for finger in ("Middle", "Ring", "Pinky"):
            for joint in (1, 2, 3):
                bone = armature.pose.bones[f"{PREFIX}{side}Hand{finger}{joint}"]
                bone.rotation_mode = "XYZ"
                bone.rotation_euler = (amount, 0.0, 0.0)
                bone.keyframe_insert(data_path="rotation_euler", frame=frame)

        for joint, bend in ((1, amount * 0.45), (2, amount * 0.7), (3, amount * 0.45)):
            thumb = armature.pose.bones[f"{PREFIX}{side}HandThumb{joint}"]
            thumb.rotation_mode = "XYZ"
            thumb.rotation_euler = (bend, 0.0, 0.0)
            thumb.keyframe_insert(data_path="rotation_euler", frame=frame)


def main() -> None:
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = START_FRAME
    scene.frame_end = END_FRAME

    armature = bpy.data.objects.get(ARMATURE_NAME)
    if armature is None or armature.type != "ARMATURE":
        raise RuntimeError(f"Expected an armature named {ARMATURE_NAME!r}")

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.transforms_clear()

    previous_action = bpy.data.actions.get(ACTION_NAME)
    if previous_action is not None:
        bpy.data.actions.remove(previous_action)

    action = bpy.data.actions.new(ACTION_NAME)
    armature.animation_data_create()
    armature.animation_data.action = action

    targets: dict[str, bpy.types.Object] = {}
    for side in ("Left", "Right"):
        targets[f"{side}_wrist"] = create_target(f"_{ACTION_NAME}_{side}_wrist", (0, 0, 0))
        targets[f"{side}_pole"] = create_target(f"_{ACTION_NAME}_{side}_pole", (0, 0, 0))
        targets[f"{side}_orientation"] = create_target(
            f"_{ACTION_NAME}_{side}_orientation", (0, 0, 0)
        )
        add_arm_constraints(
            armature,
            side,
            targets[f"{side}_wrist"],
            targets[f"{side}_pole"],
            targets[f"{side}_orientation"],
        )

    # Neutral stance: relaxed arms near the body.
    neutral = {
        "Left_wrist": (0.30, -0.04, 1.02),
        "Right_wrist": (-0.30, -0.04, 1.02),
        "Left_pole": (0.58, -0.02, 1.18),
        "Right_pole": (-0.58, -0.02, 1.18),
    }

    # PDF reference: the left index is horizontal and the right index rises
    # vertically to meet it, forming a clear plus shape in front of the chest.
    sign_pose = {
        "Left_wrist": (0.25, -0.20, 1.38),
        "Right_wrist": (0.055, -0.22, 1.19),
        "Left_pole": (0.55, -0.05, 1.23),
        "Right_pole": (-0.43, -0.06, 1.22),
    }

    for frame in (START_FRAME, 10, 62, END_FRAME):
        for key, location in neutral.items():
            keyframe_location(targets[key], frame, location)
        set_orientation(
            targets["Left_orientation"], frame, (0.0, 0.0, -1.0), (0.0, -1.0, 0.0)
        )
        set_orientation(
            targets["Right_orientation"], frame, (0.0, 0.0, -1.0), (0.0, -1.0, 0.0)
        )
        keyframe_finger_curl(armature, frame, 0.0)

    for frame in (26, 46):
        for key, location in sign_pose.items():
            keyframe_location(targets[key], frame, location)
        set_orientation(
            targets["Left_orientation"], frame, (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0)
        )
        set_orientation(
            targets["Right_orientation"], frame, (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)
        )
        keyframe_finger_curl(armature, frame, math.radians(68))

    # Bake evaluated IK and hand orientation into ordinary bone keyframes so
    # the clip works in glTF viewers without Blender constraints.
    scene.frame_set(START_FRAME)
    bpy.ops.nla.bake(
        frame_start=START_FRAME,
        frame_end=END_FRAME,
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

    for other_action in list(bpy.data.actions):
        if other_action != action:
            bpy.data.actions.remove(other_action)

    action.name = ACTION_NAME
    action.use_fake_user = True
    scene.frame_set(START_FRAME)

    OUTPUT_BLEND.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_GLB.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND), check_existing=False)

    # Preserve full-resolution textures in the editable .blend, but resize the
    # in-memory copies before web export. The avatar is displayed in a compact
    # tutor panel, so 1024 px keeps good visual quality without a 50+ MB GLB.
    web_texture_dir = Path(tempfile.mkdtemp(prefix="louise_web_textures_"))
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
        texture_path = web_texture_dir / image.name
        image.filepath_raw = str(texture_path)
        image.file_format = "PNG"
        image.save()
        image.filepath_raw = str(texture_path)

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
    shutil.rmtree(web_texture_dir, ignore_errors=True)

    print(f"Created action: {ACTION_NAME}")
    print(f"Editable Blender output: {OUTPUT_BLEND}")
    print(f"Web GLB output: {OUTPUT_GLB}")


if __name__ == "__main__":
    main()
