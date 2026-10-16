"""Source-referenced draft correction of numbers 6–9 on the Louise rig.

The old asset counts these as two-handed 5+n. The SLSL Dictionary reference
videos show one-handed thumb-based shapes. Only existing same-rig open/closed
finger rotations and the audited one-hand number arm path are used. This is
manual source transcription for review, not motion capture or SLSL approval.
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
    append_float_accessor, load_glb, write_glb,
)
from repair_master_arm_roll import Rig, angle
from audit_master_motion import slerp

SOURCE_SHA256 = "bc3aefd5a335199ec3936087060f9aaadb184b23a2246b288cd119d029ea2c4a"
EXTENDED = {
    6: {"Thumb", "Pinky"},
    7: {"Thumb", "Index"},
    8: {"Thumb", "Index", "Middle"},
    9: {"Thumb", "Index", "Middle", "Ring"},
}


def build(source: Path, output: Path) -> dict:
    if source.resolve() == output.resolve() or output.resolve() == DEFAULT_MASTER.resolve():
        raise ValueError("Build a separate candidate; never overwrite the source")
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Unexpected source; expected the 83-action master")
    original, original_binary = load_glb(source)
    doc, binary = copy.deepcopy(original), bytearray(original_binary)
    rig = Rig(original, original_binary)
    reference_action = next(a for a in original["animations"] if a["name"] == "NUMBER_1")
    key_times = reference_action["extras"]["posture_repair"]["key_times"]
    hold_start, hold_end = key_times[2:4]
    duration = key_times[-1]
    opened = rig.pose("NUMBER_5", hold_start)
    closed = rig.pose("NUMBER_0", hold_start)
    neutral = rig.pose("IDLE", 0)
    # Extended fingers may have static legacy tracks ending before the retimed
    # clip does. The moving arm provides the full 60 Hz, neutral-to-neutral grid.
    common_times = rig.tracks["NUMBER_1"][rig.names["mixamorig8:RightArm"]][0]
    time_accessor = append_float_accessor(doc, binary, [(t,) for t in common_times], "SCALAR", include_minmax=True)
    changed = []
    for animation in doc["animations"]:
        name = animation["name"]
        if name not in {f"NUMBER_{n}" for n in EXTENDED}:
            continue
        number = int(name.split("_")[-1])
        # The repaired NUMBER_1 already presents the right palm with the left
        # hand at rest. Reuse its exact timing, arm, wrist and body tracks.
        animation.update(copy.deepcopy(reference_action))
        animation["name"] = name
        for channel in animation["channels"]:
            node = channel["target"]["node"]
            node_name = rig.nodes[node].get("name", "")
            finger = next((f for f in ("Thumb", "Index", "Middle", "Ring", "Pinky")
                           if node_name.startswith(f"mixamorig8:RightHand{f}")), None)
            if finger is None:
                continue
            target = opened[node] if finger in EXTENDED[number] else closed[node]
            rotations = []
            for time in common_times:
                if time <= key_times[1] or time >= key_times[4]:
                    weight = 0.0
                elif time < hold_start:
                    weight = (time - key_times[1]) / (hold_start - key_times[1])
                elif time <= hold_end:
                    weight = 1.0
                else:
                    weight = (key_times[4] - time) / (key_times[4] - hold_end)
                weight = weight * weight * (3 - 2 * weight)
                rotations.append(tuple(slerp(neutral[node], target, weight)))
            sampler = animation["samplers"][channel["sampler"]]
            sampler["input"] = time_accessor
            sampler["output"] = append_float_accessor(doc, binary, rotations, "VEC4")
        animation["extras"]["slsl_number_reference"] = {
            "source_url": f"https://cdn.srilankansignlanguage.org/media/{number}.mp4",
            "extended_fingers": sorted(EXTENDED[number]),
            "handedness": "right_one_handed",
            "language_validation": "none", "review_required": True,
        }
        changed.append(name)
    doc.setdefault("extras", {})["slsl_number_handshape_revision"] = {
        "source_sha256": SOURCE_SHA256, "actions_changed": changed,
        "unchanged_actions": 79, "method": "manual_reference_handshape_transcription",
        "language_validation": "none", "review_required": True,
    }
    write_glb(output, doc, binary)
    candidate, candidate_binary = load_glb(output)
    candidate_rig = Rig(candidate, candidate_binary)
    # Verify every retained action and all non-number content exactly.
    for name, tracks in rig.tracks.items():
        if name not in changed and candidate_rig.tracks[name] != tracks:
            raise ValueError(f"Unrelated action changed: {name}")
        if name in changed:
            for node, (_, rotations) in candidate_rig.tracks[name].items():
                if max(angle(neutral[node], rotations[0]), angle(neutral[node], rotations[-1])) > 0.001:
                    raise ValueError(f"Neutral endpoint mismatch: {name}/{node}")
    for key in ("nodes", "skins", "meshes", "images", "textures", "materials"):
        if original.get(key) != candidate.get(key):
            raise ValueError(f"Unexpected model change: {key}")
    return {
        "source_sha256": SOURCE_SHA256,
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "actions_changed": changed, "unchanged_actions": 79,
        "rig_mesh_skin_materials_unchanged": True,
        "arm_wrist_body_path_source": "NUMBER_1",
        "language_validation": "none", "review_required": True,
        "duration_seconds": duration,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--output", type=Path, default=ROOT / "tmp/slsl-number-review/louise_slsl_numbers.glb")
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    report = build(args.source, args.output)
    if args.promote:
        if hashlib.sha256(DEFAULT_MASTER.read_bytes()).hexdigest() != SOURCE_SHA256:
            raise ValueError("Master changed; refusing installation")
        if CANONICAL_MANIFEST.read_bytes() != BUNDLED_MANIFEST.read_bytes():
            raise ValueError("Canonical and bundled manifests differ")
        manifest = json.loads(CANONICAL_MANIFEST.read_text())
        if manifest.get("master_avatar_sha256") != SOURCE_SHA256:
            raise ValueError("Source manifest does not match the original master")
        saved = args.output.parent / "louise_signs_master_before_number_revision.glb"
        if saved.exists() and hashlib.sha256(saved.read_bytes()).hexdigest() != SOURCE_SHA256:
            raise ValueError("Backup path contains another asset")
        if not saved.exists():
            shutil.copyfile(DEFAULT_MASTER, saved)
        saved_manifest = args.output.parent / "signs_before_number_revision.json"
        if saved_manifest.exists() and saved_manifest.read_bytes() != CANONICAL_MANIFEST.read_bytes():
            raise ValueError("Manifest backup path contains another revision")
        if not saved_manifest.exists():
            saved_manifest.write_bytes(CANONICAL_MANIFEST.read_bytes())
        manifest["master_avatar_sha256"] = report["output_sha256"]
        manifest["version"] = "1.5.0"
        for entry in manifest["signs"]:
            if entry["id"] == "NUMBER_0":
                entry["prototype_ready"] = False
                entry["notes"] = "Playback withheld: the legacy closed-fist gesture does not match the circular handshape in SLSL Dictionary 0.mp4. Reauthor and review before enabling."
            if entry["id"] in report["actions_changed"]:
                entry["animation_type"] = "source_referenced_prototype_gesture"
                entry["validation_status"] = "needs_validation"
                entry["notes"] = "One-handed thumb-based handshape transcribed from SLSL Dictionary reference video. Existing audited right-arm motion reused. Orientation, placement, transitions and intelligibility still require SLSL reviewer approval."
        manifest["notes"].append("Numbers 6–9 now use source-referenced one-handed thumb-based shapes instead of generic two-hand 5+n counting; all remain needs_validation.")
        staged = DEFAULT_MASTER.with_suffix(".glb.tmp")
        shutil.copyfile(args.output, staged)
        staged.replace(DEFAULT_MASTER)
        rendered = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        CANONICAL_MANIFEST.write_text(rendered)
        BUNDLED_MANIFEST.write_text(rendered)
    (args.output.parent / "number_revision_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
