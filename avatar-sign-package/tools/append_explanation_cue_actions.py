"""Append short review-only cues using exact movements from the 71-action asset.

Each new cue covers one teaching topic. These are combinations of existing
educational gestures, not newly authored or validated lexical signs.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path

from append_composite_prototype_actions import (
    BUNDLED_MANIFEST, CANONICAL_MANIFEST, DEFAULT_MASTER, ROOT,
    composite_animation, load_glb, write_glb,
)
from append_teaching_prototype_actions import verify_append

SOURCE_SHA256 = "27ca27d9a207128740d54cebe3ec76fda8d6f4af1ac3f31092bfbd63337f379d"
REVIEW_DIR = ROOT / "tmp/avatar-explanation-cues"
RECIPES = {
    "CUE_EQUATION_BALANCE": (("EQUATION", 1.0), ("BALANCE", 1.0)),
    "CUE_EQUAL_SIDES": (("BOTH_SIDES", 1.0), ("BALANCE", 1.0)),
    "CUE_ISOLATE_VARIABLE": (("VARIABLE", 1.0), ("SOLVE", 1.0)),
    "CUE_SUBTRACT_BOTH": (("SUBTRACTION", 1.0), ("BOTH_SIDES", 1.0)),
    "CUE_ADD_BOTH": (("ADDITION", 1.0), ("BOTH_SIDES", 1.0)),
    "CUE_DIVIDE_BOTH": (("DIVISION", 1.0), ("BOTH_SIDES", 1.0)),
    "CUE_MULTIPLY_BOTH": (("MULTIPLICATION", 1.0), ("BOTH_SIDES", 1.0)),
    "CUE_INVERSE_ADDITION": (("ADDITION", 1.0), ("SUBTRACTION", 1.0)),
    "CUE_INVERSE_MULTIPLICATION": (("MULTIPLICATION", 1.0), ("DIVISION", 1.0)),
    "CUE_SUBSTITUTE_ANSWER": (("ANSWER", 1.0), ("SUBSTITUTION", 1.0)),
    "CUE_VERIFY_EQUALITY": (("SUBSTITUTION", 1.0), ("BALANCE", 1.0)),
    "CUE_COLLECT_VARIABLE": (("VARIABLE", 1.0), ("BOTH_SIDES", 1.0)),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--source-manifest", type=Path, default=CANONICAL_MANIFEST)
    parser.add_argument("--output", type=Path, default=REVIEW_DIR / "louise_explanation_cues.glb")
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if source == output or output == DEFAULT_MASTER.resolve():
        raise ValueError("Build a separate candidate; --promote handles installation")
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Expected the unchanged 71-action source")
    original, original_binary = load_glb(source)
    manifest_before = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    if len(original["animations"]) != 71 or manifest_before["master_avatar_sha256"] != SOURCE_SHA256:
        raise ValueError("Source asset and manifest must match the 71-action version")
    if {entry["id"] for entry in manifest_before["signs"]} & set(RECIPES):
        raise ValueError("Explanation cues already exist")
    document, binary = copy.deepcopy(original), bytearray(original_binary)
    sources = {animation["name"]: animation for animation in original["animations"]}
    for name, recipe in RECIPES.items():
        document["animations"].append(composite_animation(document, binary, sources, name, recipe))
    document.setdefault("extras", {})["explanation_cue_expansion"] = {
        "source_sha256": SOURCE_SHA256,
        "existing_actions_preserved": 71,
        "cue_actions_added": len(RECIPES),
        "language_validation": "none",
        "review_required": True,
    }
    verify_append(original, original_binary, document, binary, RECIPES)
    write_glb(output, document, binary)
    result, result_binary = load_glb(output)
    durations = verify_append(original, original_binary, result, result_binary, RECIPES)
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest = copy.deepcopy(manifest_before)
    manifest["version"] = "1.4.0"
    manifest["master_avatar_sha256"] = checksum
    manifest["notes"].append(
        "12 short explanation-topic cues concatenate unchanged existing rotations at original speed. Not new lexical signs or full sentence translations; human review required."
    )
    for index, (name, recipe) in enumerate(RECIPES.items()):
        manifest["signs"].append({
            "id": name, "label": name.replace("_", " ").title(),
            "category": "explanation_cue", "priority": 120 + index,
            "required_for_research": False, "aliases": [],
            "clip": f"clips/{name}.glb",
            "animation_asset": "/models/louise_signs_master.glb",
            "animation_action": name, "prototype_ready": True,
            "animation_type": "composite_prototype_educational_gesture",
            "validation_status": "needs_validation",
            "notes": "Review-only topic cue: " + " → ".join(n for n, _ in recipe)
                     + ". Exact source rotations and neutral joins preserved; not a validated phrase.",
        })
    report = {
        "source_sha256": SOURCE_SHA256, "output_sha256": checksum,
        "existing_actions_preserved": 71, "new_actions": durations,
        "rig_mesh_skin_materials_textures_unchanged": True,
        "original_binary_prefix_unchanged": True,
        "source_rotations_unchanged_in_new_clips": True,
        "neutral_joins_checked": True,
        "limitations": "Source pose limitations remain. No visual, collision or linguistic approval is claimed.",
    }
    if args.promote:
        if hashlib.sha256(DEFAULT_MASTER.read_bytes()).hexdigest() != SOURCE_SHA256:
            raise ValueError("Master changed; refusing installation")
        # Preserve both manifests as well as the GLB before any replacement.
        if CANONICAL_MANIFEST.read_bytes() != BUNDLED_MANIFEST.read_bytes():
            raise ValueError("Deployment manifest differs; resolve before installation")
        if json.loads(CANONICAL_MANIFEST.read_text(encoding="utf-8")) != manifest_before:
            raise ValueError("Canonical manifest changed; refusing installation")
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        backup = REVIEW_DIR / "louise_signs_master_71_actions.glb"
        if backup.exists() and hashlib.sha256(backup.read_bytes()).hexdigest() != SOURCE_SHA256:
            raise ValueError("An unrelated backup exists")
        if not backup.exists():
            shutil.copyfile(DEFAULT_MASTER, backup)
        saved_manifest = REVIEW_DIR / "signs_71_actions.json"
        if saved_manifest.exists() and json.loads(saved_manifest.read_text(encoding="utf-8")) != manifest_before:
            raise ValueError("An unrelated manifest backup exists")
        saved_manifest.write_text(json.dumps(manifest_before, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary = DEFAULT_MASTER.with_suffix(".glb.tmp")
        shutil.copyfile(output, temporary)
        temporary.replace(DEFAULT_MASTER)
        rendered = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        CANONICAL_MANIFEST.write_text(rendered, encoding="utf-8")
        BUNDLED_MANIFEST.write_text(rendered, encoding="utf-8")
        report["backup"] = str(backup)
    (output.parent / "explanation_cues_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
