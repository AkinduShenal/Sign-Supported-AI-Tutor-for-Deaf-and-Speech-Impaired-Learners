"""Render a contact sheet source set for visual QA of tutor sign actions.

Run from the repository root:

    /Applications/Blender.app/Contents/MacOS/Blender \
      -b avatar/louise_tutor_with_signs.blend \
      --python avatar/render_sign_previews.py
"""

from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(bpy.path.abspath("//")).parent
OUTPUT_DIR = ROOT / "avatar" / "previews"
ARMATURE_NAME = "Armature"
PREVIEW_ACTIONS = (
    "IDLE",
    "ADDITION",
    "SUBTRACTION",
    "EQUATION",
    "BALANCE",
    "ALGEBRA",
    "SUBSTITUTION",
    "NUMBER_3",
    "NUMBER_4",
    "NUMBER_5",
    "NUMBER_7",
)
PREVIEW_FRAMES = {
    "SUBSTITUTION": (22, 38, 48),
}


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def prepare_scene() -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x = 480
    scene.render.resolution_y = 560
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.92, 0.92, 0.96)

    camera_data = bpy.data.cameras.new("SignPreviewCamera")
    camera = bpy.data.objects.new("SignPreviewCamera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -4.2, 1.25)
    camera.data.lens = 62
    point_at(camera, Vector((0.0, 0.0, 1.15)))
    scene.camera = camera


def main() -> None:
    armature = bpy.data.objects.get(ARMATURE_NAME)
    if armature is None:
        raise RuntimeError(f"Missing {ARMATURE_NAME!r}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prepare_scene()

    for action_name in PREVIEW_ACTIONS:
        action = bpy.data.actions.get(action_name)
        if action is None:
            continue
        frames = PREVIEW_FRAMES.get(
            action_name,
            (15,) if action_name == "IDLE" else (38,),
        )
        for frame in frames:
            armature.animation_data_create()
            armature.animation_data.action = action
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            bpy.context.scene.render.filepath = str(
                OUTPUT_DIR / f"{action_name}_{frame}.png"
            )
            bpy.ops.render.render(write_still=True)

    armature.animation_data.action = None
    print(f"Rendered sign previews to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
