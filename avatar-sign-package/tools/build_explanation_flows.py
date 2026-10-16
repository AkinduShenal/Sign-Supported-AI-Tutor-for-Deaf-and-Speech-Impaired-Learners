"""Bake connected teaching demonstrations on the existing Louise skeleton.

These are semantic teaching choreographies, not certified SLSL translations.
Look/above/put poses are manual adaptations of cited SLSL videos. Mathematics
strokes reuse the existing draft library. Each action has an actual-time cue
sheet for the player; no motion is generated during lesson requests.
"""
from __future__ import annotations

import argparse
import bisect
import copy
import hashlib
import json
import math
import shutil
import struct
from pathlib import Path

from append_composite_prototype_actions import (
    BUNDLED_MANIFEST, CANONICAL_MANIFEST, DEFAULT_MASTER, ROOT,
    append_float_accessor, load_glb, write_glb,
)
from audit_master_motion import slerp
from repair_master_arm_roll import Rig, angle, between, inv, normalize, qm, rotate

SOURCE_SHA = "c8aad3c97da38389380eaa7c5edc14176a4340880bc18926ffe576b5e738c214"
REVIEW = ROOT / "tmp/explanation-flow-review"
REFERENCES = [
    {"title": "look at", "url": "https://cdn.srilankansignlanguage.org/media/2026_Voc_look_at.mp4", "language": "sqs", "source": "SLSL Dictionary"},
    {"title": "above", "url": "https://cdn.srilankansignlanguage.org/media/2026_Voc_above_kJTR0sL.mp4", "language": "sqs", "source": "SLSL Dictionary"},
    {"title": "put", "url": "https://cdn.srilankansignlanguage.org/media/SLCFD_Verbs_Put.mp4", "language": "sqs", "source": "SLSL Dictionary"},
]

# Role, pose/stroke. No arbitrary Sinhala word is assigned a lexical sign.
RECIPES = {
    "FLOW_READ": [("look", "LOOK"), ("reference", "POINT"), ("equation", "EQUATION")],
    "FLOW_EQUALITY": [("left", "LEFT"), ("right", "POINT"), ("equal", "EQUATION")],
    "FLOW_BALANCE": [("both", "BOTH_SIDES"), ("balanced", "BALANCE"), ("equal", "EQUATION")],
    "FLOW_UNBALANCED": [("both", "BOTH_SIDES"), ("one_side", "ABOVE"), ("compare", "EQUATION")],
    "FLOW_VARIABLE": [("reference", "LOOK"), ("variable", "POINT"), ("unknown", "VARIABLE")],
    "FLOW_VARIABLE_NOT_MULTIPLY": [("variable", "POINT"), ("not_multiply", "MULTIPLICATION"), ("variable", "POINT")],
    "FLOW_ISOLATE": [("variable", "VARIABLE"), ("one_side", "LEFT"), ("isolate", "SOLVE")],
    "FLOW_ADD_BOTH": [("both", "BOTH_SIDES"), ("add", "ADDITION"), ("equal", "EQUATION")],
    "FLOW_SUBTRACT_BOTH": [("both", "BOTH_SIDES"), ("subtract", "SUBTRACTION"), ("equal", "EQUATION")],
    "FLOW_MULTIPLY_BOTH": [("both", "BOTH_SIDES"), ("multiply", "MULTIPLICATION"), ("equal", "EQUATION")],
    "FLOW_DIVIDE_BOTH": [("both", "BOTH_SIDES"), ("divide", "DIVISION"), ("equal", "EQUATION")],
    "FLOW_INVERSE_ADD": [("add", "ADDITION"), ("undo_subtract", "SUBTRACTION"), ("isolate", "SOLVE")],
    "FLOW_INVERSE_SUBTRACT": [("subtract", "SUBTRACTION"), ("undo_add", "ADDITION"), ("isolate", "SOLVE")],
    "FLOW_INVERSE_MULTIPLY": [("multiply", "MULTIPLICATION"), ("undo_divide", "DIVISION"), ("isolate", "SOLVE")],
    "FLOW_SUBSTITUTE": [("original", "ABOVE"), ("variable", "POINT"), ("value", "LOOK"), ("place", "PUT"), ("replaced", "POINT")],
    "FLOW_CHECK": [("reference", "LOOK"), ("left", "LEFT"), ("right", "POINT"), ("equal", "EQUATION")],
    "FLOW_COLLECT": [("left", "LEFT"), ("right", "POINT"), ("collect", "SUBSTITUTION"), ("isolate", "SOLVE")],
    "FLOW_EXPAND": [("group", "BOTH_SIDES"), ("multiply", "MULTIPLICATION"), ("each_term", "LEFT"), ("each_term", "POINT")],
    "FLOW_STEP": [("reference", "LOOK"), ("one_step", "NUMBER_1"), ("continue", "POINT")],
    "FLOW_PRACTICE": [("reference", "LOOK"), ("variable", "POINT"), ("try", "SOLVE"), ("check", "EQUATION")],
    "FLOW_HINT": [("reference", "LOOK"), ("variable", "POINT"), ("one_step", "NUMBER_1")],
    "FLOW_COMPARE": [("left", "LEFT"), ("right", "POINT"), ("compare", "BOTH_SIDES")],
    "FLOW_NEGATIVE": [("reference", "LOOK"), ("negative", "SUBTRACTION"), ("keep_sign", "POINT")],
    "FLOW_RETRY": [("reference", "LOOK"), ("one_step", "NUMBER_1"), ("try", "SOLVE")],
    "FLOW_ANSWER": [("variable", "POINT"), ("value", "ANSWER"), ("check", "EQUATION")],
}
for number in range(1, 10):
    RECIPES[f"FLOW_SUBSTITUTE_{number}"] = [
        ("original", "ABOVE"), ("variable", "POINT"),
        ("value", f"NUMBER_{number}"), ("place", "PUT"), ("replaced", "POINT"),
    ]
    for operation, source in (("ADD", "ADDITION"), ("SUBTRACT", "SUBTRACTION"), ("MULTIPLY", "MULTIPLICATION"), ("DIVIDE", "DIVISION")):
        RECIPES[f"FLOW_{operation}_BOTH_{number}"] = [
            ("both", "BOTH_SIDES"), ("value", f"NUMBER_{number}"),
            (operation.lower(), source), ("equal", "EQUATION"),
        ]


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def pose_library(rig):
    neutral = rig.pose("IDLE", 0)
    poses = {"IDLE": neutral}
    for name in ("EQUATION", "BOTH_SIDES", "BALANCE", "VARIABLE", "ADDITION", "SUBTRACTION", "MULTIPLICATION", "DIVISION", "SUBSTITUTION", "SOLVE", "ANSWER", *(f"NUMBER_{n}" for n in range(1, 10))):
        animation = next(a for a in rig.doc["animations"] if a["name"] == name)
        times = animation["extras"]["posture_repair"]["key_times"]
        poses[name] = [rig.pose(name, times[2]), rig.pose(name, times[3])]
    poses["POINT"] = [rig.pose("NUMBER_1", 1.8)]
    # Left-hand index already exists in the division draft; keep only that arm
    # active for a distinct spatial reference, rather than relabelling a right point.
    left = dict(neutral)
    source = rig.pose("DIVISION", 1.9)
    for node in neutral:
        if "Left" in rig.nodes[node].get("name", ""):
            left[node] = source[node]
    poses["LEFT"] = [left]

    def raise_arm(pose, side, upper_direction, lower_direction):
        result = dict(pose)
        world = rig.world(pose)
        arm, fore, hand = [rig.names[f"mixamorig8:{side}{p}"] for p in ("Arm", "ForeArm", "Hand")]
        upper_axis = normalize(rig.nodes[fore]["translation"])
        lower_axis = normalize(rig.nodes[hand]["translation"])
        upper = qm(between(rotate(world[arm], upper_axis), upper_direction), world[arm])
        lower = qm(between(rotate(world[fore], lower_axis), lower_direction), world[fore])
        result[arm] = normalize(qm(inv(world[rig.parents[arm]]), upper))
        result[fore] = normalize(qm(inv(upper), lower))
        # Preserve the checked local wrist swing/roll; never use hand position IK.
        return result

    look = raise_arm(rig.pose("NUMBER_7", 1.8), "Right", [-.30, -.78, .55], [.18, .85, .49])
    poses["LOOK"] = [look, rig.pose("NUMBER_7", 1.8)]
    above = raise_arm(rig.pose("BOTH_SIDES", 1.9), "Right", [-.30, -.78, .55], [.18, .85, .49])
    for node in neutral:
        if "RightHand" in rig.nodes[node].get("name", "") and node != rig.names["mixamorig8:RightHand"]:
            above[node] = rig.pose("NUMBER_5", 1.8)[node]
    poses["ABOVE"] = [above]
    put = dict(rig.pose("NUMBER_4", 1.8))
    released = dict(rig.pose("NUMBER_4", 2.85))
    opened, closed = rig.pose("NUMBER_5", 1.8), rig.pose("NUMBER_0", 1.8)
    for node in neutral:
        if "RightHand" in rig.nodes[node].get("name", "") and node != rig.names["mixamorig8:RightHand"]:
            put[node] = slerp(opened[node], closed[node], .40)
            released[node] = opened[node]
    # Reference put: one hand gathers, moves down/forward, and releases. This is
    # an adapted draft; fingertip contact and precise lexical placement need review.
    poses["PUT"] = [put, released]
    return neutral, poses


def bake(doc, binary, neutral, poses, name, recipe):
    keys = [(0.0, neutral)]
    beats = []
    for role, source in recipe:
        start = keys[-1][0]
        for target in poses[source]:
            # Smoothstep has peak derivative 1.5. Bound every joint, including
            # fingers and head, to <=140 deg/s; bake at 60 Hz.
            travel = max(.7, max(angle(keys[-1][1][node], target[node]) for node in neutral) * 1.55 / 140)
            keys.append((keys[-1][0] + travel, target))
        keys.append((keys[-1][0] + .85, keys[-1][1]))
        beats.append({"role": role, "start": round(start, 6), "end": round(keys[-1][0], 6)})
    travel = max(.8, max(angle(keys[-1][1][node], neutral[node]) for node in neutral) * 1.55 / 140)
    keys.append((keys[-1][0] + travel, neutral))
    duration = keys[-1][0]
    times = sorted({f32(i / 60) for i in range(math.ceil(duration * 60))} | {f32(t) for t, _ in keys})
    times = [t for t in times if t <= f32(duration)]
    key_times = [t for t, _ in keys]
    samples = []
    for time in times:
        right = min(len(keys) - 1, bisect.bisect_right(key_times, time))
        left = max(0, right - 1)
        ratio = max(0, min(1, (time - key_times[left]) / (key_times[right] - key_times[left])))
        ratio = ratio * ratio * (3 - 2 * ratio)
        samples.append({node: normalize(slerp(keys[left][1][node], keys[right][1][node], ratio)) for node in neutral})
    # Float rounding at the last key must not leave an almost-neutral endpoint.
    samples[0], samples[-1] = neutral, neutral
    input_index = append_float_accessor(doc, binary, [(t,) for t in times], "SCALAR", include_minmax=True)
    channels, samplers = [], []
    idle = next(a for a in doc["animations"] if a["name"] == "IDLE")
    idle_samplers = {c["target"]["node"]: idle["samplers"][c["sampler"]] for c in idle["channels"]}
    for node in neutral:
        values = [tuple(pose[node]) for pose in samples]
        channels.append({"sampler": len(samplers), "target": {"node": node, "path": "rotation"}})
        if all(angle(neutral[node], value) < .00001 for value in values):
            # Constant body/finger channels reuse the exact neutral track.
            samplers.append(copy.deepcopy(idle_samplers[node]))
        else:
            output = append_float_accessor(doc, binary, values, "VEC4")
            samplers.append({"input": input_index, "output": output, "interpolation": "LINEAR"})
    return {"name": name, "channels": channels, "samplers": samplers,
            "extras": {"explanation_flow": {"beats": beats, "duration": f32(duration),
                       "recipe": recipe, "language_validation": "none", "review_required": True}}}


def build(source, output):
    if source.resolve() == output.resolve() or output.resolve() == DEFAULT_MASTER.resolve():
        raise ValueError("A separate candidate is required")
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError("Expected the unchanged 83-action number revision")
    original, old_binary = load_glb(source)
    doc, binary = copy.deepcopy(original), bytearray(old_binary)
    rig = Rig(original, old_binary)
    neutral, poses = pose_library(rig)
    for name, recipe in RECIPES.items():
        doc["animations"].append(bake(doc, binary, neutral, poses, name, recipe))
    doc.setdefault("extras", {})["explanation_flow_revision"] = {
        "source_sha256": SOURCE_SHA, "original_actions_preserved": 83,
        "actions_added": len(RECIPES), "language_validation": "none", "review_required": True,
    }
    write_glb(output, doc, binary)
    result, result_binary = load_glb(output)
    check = Rig(result, result_binary)
    assert all(check.tracks[name] == tracks for name, tracks in rig.tracks.items())
    assert all(doc.get(k) == original.get(k) for k in ("nodes", "meshes", "skins", "materials", "images", "textures"))
    assert all(max(angle(neutral[node], values[0]), angle(neutral[node], values[-1])) < .001
               for name in RECIPES for node, (_, values) in check.tracks[name].items())
    return doc, hashlib.sha256(output.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--output", type=Path, default=REVIEW / "louise_explanation_flows.glb")
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    doc, checksum = build(args.source, args.output)
    if args.promote:
        if hashlib.sha256(DEFAULT_MASTER.read_bytes()).hexdigest() != SOURCE_SHA:
            raise ValueError("Current master changed")
        raw = CANONICAL_MANIFEST.read_bytes()
        if raw != BUNDLED_MANIFEST.read_bytes():
            raise ValueError("Deployment manifest differs")
        manifest = json.loads(raw)
        if manifest["master_avatar_sha256"] != SOURCE_SHA:
            raise ValueError("Manifest does not match source")
        for name, data in (("master_before_flows.glb", DEFAULT_MASTER.read_bytes()), ("signs_before_flows.json", raw)):
            saved = args.output.parent / name
            if saved.exists() and saved.read_bytes() != data:
                raise ValueError("Unrelated backup exists")
            if not saved.exists():
                saved.write_bytes(data)
        manifest["version"] = "1.6.0"
        manifest["master_avatar_sha256"] = checksum
        for action in doc["animations"]:
            if action["name"] not in RECIPES:
                continue
            flow = action["extras"]["explanation_flow"]
            references = []
            words = {source for _, source in RECIPES[action["name"]]}
            for word, reference in zip(("LOOK", "ABOVE", "PUT"), REFERENCES):
                if word in words:
                    references.append(reference)
            for entry in manifest["signs"]:
                if entry["id"] in words:
                    references.extend(entry.get("reference_videos", []))
            references = list({reference["url"]: reference for reference in references}.values())
            manifest["signs"].append({
                "id": action["name"], "label": action["name"].replace("FLOW_", "").replace("_", " ").title(),
                "category": "explanation_flow", "priority": 160, "required_for_research": False,
                "aliases": [], "clip": f"clips/{action['name']}.glb",
                "animation_asset": "/models/louise_signs_master.glb", "animation_action": action["name"],
                "prototype_ready": True, "animation_type": "source_referenced_teaching_demonstration",
                "validation_status": "needs_validation", "teaching_beats": flow["beats"],
                "duration_seconds": flow["duration"], "reference_videos": references,
                "notes": "Connected semantic demonstration. Look/above/put are source-referenced manual adaptations; math motions reuse unvalidated drafts. Not certified SLSL sentence grammar.",
            })
        manifest["notes"].append("Connected explanation flows with actual-time semantic beats cover introductions, worked steps, hints and source-based Q&A. They remain draft demonstrations, not validated SLSL translations.")
        staged = DEFAULT_MASTER.with_suffix(".glb.tmp")
        shutil.copyfile(args.output, staged)
        staged.replace(DEFAULT_MASTER)
        rendered = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        CANONICAL_MANIFEST.write_text(rendered)
        BUNDLED_MANIFEST.write_text(rendered)
    report = {"source_sha256": SOURCE_SHA, "output_sha256": checksum,
              "preserved_actions": 83, "new_actions": len(RECIPES),
              "language_validation": "none", "review_required": True}
    (args.output.parent / "flow_build_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
