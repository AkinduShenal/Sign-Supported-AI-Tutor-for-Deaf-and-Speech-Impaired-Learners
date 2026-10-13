"""Append longer teaching demos using unchanged, repaired Louise movements.

No poses, signs, skeleton transforms, skin weights or facial motion are invented.
Every new clip concatenates existing neutral-to-neutral tracks at their original
speed or slower. These are review-only teaching demonstrations, not SLSL phrases.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import shutil
from pathlib import Path

from append_composite_prototype_actions import (
    CANONICAL_MANIFEST, BUNDLED_MANIFEST, DEFAULT_MASTER, ROOT,
    animation_tracks, composite_animation, load_glb, write_glb,
)

SOURCE_SHA256 = "dbecc512846c3a0bd1d3198c020f313eef017272a2e9df7a2f850d3000729fa9"
REVIEW_DIR = ROOT / "tmp/avatar-animation-expansion"

# The words describe the teaching topic, not the linguistic meaning of the
# constituent gestures. Human review/replacement remains explicit in manifest.
RECIPES = {
    "EXPLAIN_EQUALITY": (("EQUATION", 1.0), ("BALANCE", 1.0), ("BOTH_SIDES", 1.0)),
    "EXPLAIN_UNKNOWN_VARIABLE": (("EQUATION", 1.0), ("VARIABLE", 1.0), ("SOLVE", 1.0)),
    "EXPLAIN_UNDO_ADDITION": (("ADDITION", 1.0), ("SUBTRACTION", 1.0), ("BOTH_SIDES", 1.0)),
    "EXPLAIN_UNDO_SUBTRACTION": (("SUBTRACTION", 1.0), ("ADDITION", 1.0), ("BOTH_SIDES", 1.0)),
    "EXPLAIN_DIVIDE_COEFFICIENT": (("MULTIPLICATION", 1.0), ("DIVISION", 1.0), ("BOTH_SIDES", 1.0), ("VARIABLE", 1.0)),
    "EXPLAIN_EXPAND_BRACKETS": (("MULTIPLICATION", 1.0), ("BOTH_SIDES", 1.0), ("EQUATION", 1.0)),
    "EXPLAIN_CLEAR_DENOMINATOR": (("DIVISION", 1.0), ("MULTIPLICATION", 1.0), ("BOTH_SIDES", 1.0)),
    "EXPLAIN_COLLECT_VARIABLES": (("VARIABLE", 1.0), ("BOTH_SIDES", 1.0), ("EQUATION", 1.0)),
    "EXPLAIN_CHECK_SOLUTION": (("ANSWER", 1.0), ("SUBSTITUTION", 1.0), ("EQUATION", 1.0)),
    "EXPLAIN_SOLUTION_FOUND": (("VARIABLE", 1.0), ("SOLVE", 1.0), ("ANSWER", 1.0)),
    "TEACH_STEP_BY_STEP": (("EQUATION", 1.15), ("VARIABLE", 1.15), ("BOTH_SIDES", 1.15), ("SOLVE", 1.15)),
    "TEACH_CONCEPTUAL": (("EQUATION", 1.1), ("BALANCE", 1.1), ("BOTH_SIDES", 1.1)),
    "TEACH_WORKED_EXAMPLE": (("EQUATION", 1.0), ("SOLVE", 1.0), ("ANSWER", 1.0), ("SUBSTITUTION", 1.0)),
    "TEACH_PROGRESSIVE_HINTS": (("VARIABLE", 1.1), ("BOTH_SIDES", 1.1), ("SOLVE", 1.1)),
    "TEACH_INDEPENDENT_CHALLENGE": (("EQUATION", 1.0), ("VARIABLE", 1.0), ("SOLVE", 1.0), ("SUBSTITUTION", 1.0)),
}


def verify_append(original, original_binary, result, result_binary, recipes=RECIPES):
    """Reject anything beyond appended animation/accessor/BIN data."""
    allowed = {"animations", "accessors", "bufferViews", "buffers", "extras"}
    for key in set(original) | set(result):
        if key not in allowed and original.get(key) != result.get(key):
            raise ValueError(f"Existing {key} changed")
    for key in ("animations", "accessors", "bufferViews"):
        if result[key][:len(original[key])] != original[key]:
            raise ValueError(f"Existing {key} changed")
    if result_binary[:len(original_binary)] != original_binary:
        raise ValueError("Original mesh/skin/texture/animation binary data changed")
    if len(result["animations"]) != len(original["animations"]) + len(recipes):
        raise ValueError("Unexpected animation count")
    if len({action["name"] for action in result["animations"]}) != len(result["animations"]):
        raise ValueError("Duplicate animation name")
    original_buffers = copy.deepcopy(original["buffers"])
    resulting_buffers = copy.deepcopy(result["buffers"])
    resulting_buffers[0]["byteLength"] = original_buffers[0]["byteLength"]
    if original_buffers != resulting_buffers:
        raise ValueError("Buffer metadata beyond appended byte length changed")
    for key, value in original.get("extras", {}).items():
        if result.get("extras", {}).get(key) != value:
            raise ValueError(f"Existing provenance {key} changed")

    sources = {a["name"]: animation_tracks(original, original_binary, a)
               for a in original["animations"]}
    durations = {}
    for animation in result["animations"][len(original["animations"]):]:
        recipe = recipes[animation["name"]]
        tracks = animation_tracks(result, result_binary, animation)
        source_nodes = set(sources[recipe[0][0]])
        if set(tracks) != source_nodes:
            raise ValueError("New clip changes the set of animated bones")
        for node, (times, rotations) in tracks.items():
            expected = [rotation for name, scale in recipe for rotation in sources[name][node][1]]
            if rotations != expected:
                raise ValueError("An existing hand/body rotation was altered")
            if any(not math.isfinite(t) for t in times) or any(b <= a for a, b in zip(times, times[1:])):
                raise ValueError("Invalid float32 animation key times")
            if any(abs(sum(v * v for v in rotation) - 1) > 1e-5 for rotation in rotations):
                raise ValueError("Invalid rotation quaternion")
            neutral = sources["IDLE"][node][1][0]
            for endpoint in (rotations[0], rotations[-1]):
                if abs(sum(a * b for a, b in zip(endpoint, neutral))) < 0.999999:
                    raise ValueError("New clip has a mismatched neutral endpoint")
            # Every join is between the same existing neutral rotations. All
            # time scales are >=1, so no source motion is made faster.
            for name, scale in recipe:
                if scale < 1:
                    raise ValueError("Teaching clips must not speed up source motion")
                first, last = sources[name][node][1][0], sources[name][node][1][-1]
                if any(abs(sum(a * b for a, b in zip(endpoint, neutral))) < 0.999999 for endpoint in (first, last)):
                    raise ValueError(f"{name} has an unsafe neutral join")
        durations[animation["name"]] = round(max(t[-1] for t, _ in tracks.values()), 3)
    return durations


def new_manifest(source_manifest, checksum):
    manifest = copy.deepcopy(source_manifest)
    if {entry["id"] for entry in manifest["signs"]} & set(RECIPES):
        raise ValueError("Manifest already contains teaching expansion")
    manifest["version"] = "1.3.0"
    manifest["master_avatar_sha256"] = checksum
    manifest["notes"].append(
        "15 longer teaching-demo clips reuse unchanged repaired movements. They are composite topic cues, not new lexical signs or SLSL phrase translations. All require human review."
    )
    for index, (name, recipe) in enumerate(RECIPES.items()):
        manifest["signs"].append({
            "id": name,
            "label": name.replace("_", " ").title(),
            "category": "teaching_demo",
            "priority": 100 + index,
            "required_for_research": False,
            "aliases": [],
            "clip": f"clips/{name}.glb",
            "animation_asset": "/models/louise_signs_master.glb",
            "animation_action": name,
            "prototype_ready": True,
            "animation_type": "composite_prototype_educational_gesture",
            "validation_status": "needs_validation",
            "notes": "Review-only teaching-topic motion recipe: " + " → ".join(n for n, _ in recipe) + ". Original poses unchanged; not a validated sign or phrase.",
        })
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--source-manifest", type=Path, default=CANONICAL_MANIFEST,
                        help="Use the saved 56-action manifest when reproducing a candidate from the backup")
    parser.add_argument("--output", type=Path, default=REVIEW_DIR / "louise_teaching_review.glb")
    parser.add_argument("--promote", action="store_true", help="Back up the original and install the checked expansion plus both manifests")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if source == output or output == DEFAULT_MASTER.resolve():
        raise ValueError("Create a separate candidate; --promote handles master replacement")
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Expected the unchanged 56-action source; refusing to re-expand another asset")
    original, original_binary = load_glb(source)
    if len(original["animations"]) != 56:
        raise ValueError("Unexpected source action count")
    manifest_before = json.loads(args.source_manifest.read_text())
    if manifest_before["master_avatar_sha256"] != SOURCE_SHA256:
        raise ValueError("Canonical manifest does not match the 56-action source")
    document, binary = copy.deepcopy(original), bytearray(original_binary)
    sources = {animation["name"]: animation for animation in document["animations"]}
    for name, recipe in RECIPES.items():
        document["animations"].append(composite_animation(document, binary, sources, name, recipe))
    document.setdefault("extras", {})["teaching_prototype_expansion"] = {
        "source_sha256": SOURCE_SHA256,
        "existing_actions_preserved": len(original["animations"]),
        "teaching_actions_added": len(RECIPES),
        "language_validation": "none",
        "review_required": True,
    }
    verify_append(original, original_binary, document, binary)
    write_glb(output, document, binary)
    result, resulting_binary = load_glb(output)
    durations = verify_append(original, original_binary, result, resulting_binary)
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest = new_manifest(manifest_before, checksum)
    report = {
        "source_sha256": SOURCE_SHA256,
        "output_sha256": checksum,
        "existing_actions_preserved": len(original["animations"]),
        "new_actions": durations,
        "rig_mesh_skin_materials_textures_unchanged": True,
        "original_binary_prefix_unchanged": True,
        "source_rotations_unchanged_in_new_clips": True,
        "neutral_joins_checked": True,
        "limitations": "No visual, collision or linguistic approval is claimed. These demos reuse old movements; they do not author new lexical signs.",
    }
    if args.promote:
        if hashlib.sha256(DEFAULT_MASTER.read_bytes()).hexdigest() != SOURCE_SHA256:
            raise ValueError("Master changed while building; refusing promotion")
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        backup = REVIEW_DIR / "louise_signs_master_56_actions.glb"
        if backup.exists() and hashlib.sha256(backup.read_bytes()).hexdigest() != SOURCE_SHA256:
            raise ValueError("An unrelated backup already exists")
        if not backup.exists():
            shutil.copyfile(DEFAULT_MASTER, backup)
        (REVIEW_DIR / "signs_56_actions.json").write_text(json.dumps(manifest_before, indent=2) + "\n")
        temporary = DEFAULT_MASTER.with_suffix(".glb.tmp")
        shutil.copyfile(output, temporary)
        temporary.replace(DEFAULT_MASTER)
        rendered = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        CANONICAL_MANIFEST.write_text(rendered)
        BUNDLED_MANIFEST.write_text(rendered)
        report["installed_master"] = str(DEFAULT_MASTER)
        report["backup"] = str(backup)
    (output.parent / "teaching_expansion_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
