"""Append review-only composite actions without changing the repaired core clips.

The 34 added actions are motion-review placeholders assembled from the existing
22 technically checked actions. They are not transcriptions or validated SLSL.
Run this only against the canonical repaired 22-action source asset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MASTER = ROOT / "frontend/public/models/louise_signs_master.glb"
CANONICAL_MANIFEST = ROOT / "avatar-sign-package/manifest/signs.json"
BUNDLED_MANIFEST = ROOT / "backend/app/modules/tutor/sign_package/signs.json"
REPAIRED_CORE_SHA256 = "a4c837f03a64484bd75fe05c71a04d9bba36198811308d609c0b8fc4ad0cd5b0"

# These recipes deliberately reuse already-audited neutral-to-neutral motion.
# They are semantically suggestive placeholders for human review, not language
# claims. A later approved same-rig clip can replace any action independently.
RECIPES: dict[str, tuple[tuple[str, float], ...]] = {
    "ALGEBRA": (("VARIABLE", 1.0), ("EQUATION", 1.0)),
    "EXPRESSION": (("VARIABLE", 1.0), ("ANSWER", 1.0)),
    "TERM": (("VARIABLE", 1.0), ("NUMBER_1", 1.0)),
    "COEFFICIENT": (("NUMBER_2", 1.0), ("VARIABLE", 1.0)),
    "POSITIVE": (("ADDITION", 1.0), ("ANSWER", 1.0)),
    "NEGATIVE": (("SUBTRACTION", 1.0), ("ANSWER", 1.0)),
    "BRACKET": (("BOTH_SIDES", 1.0), ("BALANCE", 1.0)),
    "START": (("ANSWER", 1.0), ("SOLVE", 1.0)),
    "NEXT": (("ANSWER", 1.0), ("ADDITION", 1.0)),
    "PREVIOUS": (("SUBTRACTION", 1.0), ("ANSWER", 1.0)),
    "STEP": (("NUMBER_1", 1.0),),
    "EXAMPLE": (("EQUATION", 1.0), ("ANSWER", 1.0)),
    "PRACTICE": (("SOLVE", 1.0),),
    "QUESTION": (("VARIABLE", 1.0), ("BALANCE", 1.0)),
    "HINT": (("VARIABLE", 1.0), ("ANSWER", 1.0)),
    "REPEAT": (("SUBSTITUTION", 1.0), ("SUBSTITUTION", 1.0)),
    "TRY_AGAIN": (("SUBTRACTION", 1.0), ("SOLVE", 1.0)),
    "CHECK": (("SUBSTITUTION", 1.0), ("EQUATION", 1.0)),
    "CORRECT": (("EQUATION", 1.0), ("ANSWER", 1.0)),
    "INCORRECT": (("SUBTRACTION", 1.0), ("BALANCE", 1.0)),
    "FINISH": (("SOLVE", 1.0), ("ANSWER", 1.0)),
    "ERROR_CORRECTION": (("SUBTRACTION", 1.0), ("SUBSTITUTION", 1.0)),
    "FOUNDATION": (("BALANCE", 1.0), ("EQUATION", 1.0)),
    "STEP_BY_STEP": (("NUMBER_1", 1.0), ("NUMBER_2", 1.0)),
    "MATCH": (("EQUATION", 1.0),),
    "DRAG_DROP": (("SUBSTITUTION", 1.0),),
    "SIGN_KEYWORD": (("VARIABLE", 1.0), ("ANSWER", 1.0)),
    "VISUAL": (("ANSWER", 1.0), ("VARIABLE", 1.0)),
    "TEXT": (("EQUATION", 1.0), ("ANSWER", 1.0)),
    "EASY": (("ANSWER", 1.0),),
    "DIFFICULT": (("BALANCE", 1.0), ("VARIABLE", 1.0)),
    "SLOW": (("SOLVE", 1.5),),
    "IMPROVED": (("ADDITION", 1.0), ("SOLVE", 1.0)),
    "NOT_IMPROVED": (("SUBTRACTION", 1.0), ("BALANCE", 1.0)),
}


def load_glb(path: Path) -> tuple[dict, bytearray]:
    data = path.read_bytes()
    magic, version, declared_size = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or declared_size != len(data):
        raise ValueError("Expected a valid GLB 2.0 source asset")
    json_length, json_kind = struct.unpack_from("<II", data, 12)
    if json_kind != 0x4E4F534A:
        raise ValueError("Missing GLB JSON chunk")
    document = json.loads(data[20 : 20 + json_length])
    binary_header = 20 + json_length
    binary_length, binary_kind = struct.unpack_from("<II", data, binary_header)
    if binary_kind != 0x004E4942:
        raise ValueError("Missing GLB binary chunk")
    binary_start = binary_header + 8
    return document, bytearray(data[binary_start : binary_start + binary_length])


def read_float_accessor(document: dict, binary: bytearray, index: int) -> list[tuple[float, ...]]:
    accessor = document["accessors"][index]
    if accessor["componentType"] != 5126 or "sparse" in accessor:
        raise ValueError("Only dense float accessors are supported")
    components = {"SCALAR": 1, "VEC4": 4}[accessor["type"]]
    view = document["bufferViews"][accessor["bufferView"]]
    stride = view.get("byteStride", components * 4)
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    return [
        struct.unpack_from("<" + "f" * components, binary, offset + row * stride)
        for row in range(accessor["count"])
    ]


def append_float_accessor(
    document: dict,
    binary: bytearray,
    values: list[tuple[float, ...]],
    accessor_type: str,
    *,
    include_minmax: bool = False,
) -> int:
    while len(binary) % 4:
        binary.append(0)
    offset = len(binary)
    components = {"SCALAR": 1, "VEC4": 4}[accessor_type]
    for value in values:
        if len(value) != components:
            raise ValueError(f"Invalid {accessor_type} row")
        binary.extend(struct.pack("<" + "f" * components, *value))
    view_index = len(document.setdefault("bufferViews", []))
    document["bufferViews"].append(
        {"buffer": 0, "byteOffset": offset, "byteLength": len(values) * components * 4}
    )
    accessor: dict = {
        "bufferView": view_index,
        "byteOffset": 0,
        "componentType": 5126,
        "count": len(values),
        "type": accessor_type,
    }
    if include_minmax:
        accessor["min"] = [min(value[0] for value in values)]
        accessor["max"] = [max(value[0] for value in values)]
    accessor_index = len(document.setdefault("accessors", []))
    document["accessors"].append(accessor)
    return accessor_index


def animation_tracks(document: dict, binary: bytearray, animation: dict) -> dict[int, tuple[list[float], list[tuple[float, ...]]]]:
    tracks = {}
    for channel in animation["channels"]:
        if channel["target"]["path"] != "rotation":
            raise ValueError(f"{animation['name']} contains a non-rotation channel")
        sampler = animation["samplers"][channel["sampler"]]
        if sampler.get("interpolation", "LINEAR") != "LINEAR":
            raise ValueError(f"{animation['name']} contains non-linear interpolation")
        times = [row[0] for row in read_float_accessor(document, binary, sampler["input"])]
        rotations = read_float_accessor(document, binary, sampler["output"])
        tracks[channel["target"]["node"]] = (times, rotations)
    return tracks


def composite_animation(
    document: dict,
    binary: bytearray,
    sources: dict[str, dict],
    name: str,
    recipe: tuple[tuple[str, float], ...],
) -> dict:
    source_tracks = {
        source_name: animation_tracks(document, binary, sources[source_name])
        for source_name, _ in recipe
    }
    node_sets = [set(source_tracks[source_name]) for source_name, _ in recipe]
    if any(nodes != node_sets[0] for nodes in node_sets[1:]):
        raise ValueError(f"Recipe {name} uses incompatible source tracks")

    channels = []
    samplers = []
    for node in sorted(node_sets[0]):
        combined_times: list[tuple[float]] = []
        combined_rotations: list[tuple[float, ...]] = []
        offset = 0.0
        for segment_index, (source_name, time_scale) in enumerate(recipe):
            times, rotations = source_tracks[source_name][node]
            first_time = times[0]
            if segment_index:
                offset = combined_times[-1][0] + 0.10
            for time, rotation in zip(times, rotations, strict=True):
                combined_times.append((offset + (time - first_time) * time_scale,))
                combined_rotations.append(rotation)
        input_index = append_float_accessor(
            document, binary, combined_times, "SCALAR", include_minmax=True
        )
        output_index = append_float_accessor(
            document, binary, combined_rotations, "VEC4"
        )
        sampler_index = len(samplers)
        samplers.append(
            {
                "input": input_index,
                "output": output_index,
                "interpolation": "LINEAR",
            }
        )
        channels.append(
            {"sampler": sampler_index, "target": {"node": node, "path": "rotation"}}
        )

    return {
        "name": name,
        "channels": channels,
        "samplers": samplers,
        "extras": {
            "prototype_composite": {
                "language_validation": "none",
                "review_required": True,
                "recipe": [source_name for source_name, _ in recipe],
            }
        },
    }


def write_glb(path: Path, document: dict, binary: bytearray) -> None:
    while len(binary) % 4:
        binary.append(0)
    document["buffers"][0]["byteLength"] = len(binary)
    json_bytes = json.dumps(document, separators=(",", ":"), ensure_ascii=False).encode()
    while len(json_bytes) % 4:
        json_bytes += b" "
    total_size = 12 + 8 + len(json_bytes) + 8 + len(binary)
    output = bytearray(struct.pack("<4sII", b"glTF", 2, total_size))
    output.extend(struct.pack("<II", len(json_bytes), 0x4E4F534A))
    output.extend(json_bytes)
    output.extend(struct.pack("<II", len(binary), 0x004E4942))
    output.extend(binary)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(output)
    temporary.replace(path)


def update_manifests(master: Path) -> None:
    manifest = json.loads(CANONICAL_MANIFEST.read_text(encoding="utf-8"))
    manifest["version"] = "1.2.0"
    expansion_note = (
        "Composite prototype expansion adds 34 review-only actions assembled from "
        "the repaired core motions. These additions are not SLSL transcriptions and "
        "remain needs_validation until replaced or approved by a qualified reviewer."
    )
    manifest["notes"] = [
        expansion_note,
        *[note for note in manifest["notes"] if not note.startswith("Composite prototype expansion")],
    ]
    entries = {entry["id"]: entry for entry in manifest["signs"]}
    if set(RECIPES) - set(entries):
        raise ValueError(f"Recipes missing from manifest: {sorted(set(RECIPES) - set(entries))}")
    for action, recipe in RECIPES.items():
        entry = entries[action]
        entry["animation_asset"] = "/models/louise_signs_master.glb"
        entry["animation_action"] = action
        entry["prototype_ready"] = True
        entry["animation_type"] = "composite_prototype_educational_gesture"
        entry["validation_status"] = "needs_validation"
        entry["notes"] = (
            "Review-only composite motion recipe: "
            + " + ".join(source for source, _ in recipe)
            + ". Not a validated SLSL transcription."
        )
    manifest["master_avatar_sha256"] = hashlib.sha256(master.read_bytes()).hexdigest()
    rendered = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    CANONICAL_MANIFEST.write_text(rendered, encoding="utf-8")
    BUNDLED_MANIFEST.write_text(rendered, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--output", type=Path, default=DEFAULT_MASTER)
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash != REPAIRED_CORE_SHA256:
        raise ValueError(
            "Source must be the canonical repaired 22-action master from commit "
            "53b9b9b; this guard prevents overwriting an unknown or already-expanded asset."
        )
    document, binary = load_glb(source)
    sources = {animation["name"]: animation for animation in document["animations"]}
    missing_sources = {
        source_name
        for recipe in RECIPES.values()
        for source_name, _ in recipe
        if source_name not in sources
    }
    if missing_sources:
        raise ValueError(f"Missing core source actions: {sorted(missing_sources)}")
    if set(RECIPES) & set(sources):
        raise ValueError("Source already contains one or more expansion actions")
    document["animations"] = [
        *document["animations"],
        *[
            composite_animation(document, binary, sources, name, recipe)
            for name, recipe in RECIPES.items()
        ],
    ]
    document.setdefault("extras", {})["composite_prototype_expansion"] = {
        "language_validation": "none",
        "review_required": True,
        "core_actions_preserved": 22,
        "composite_actions_added": len(RECIPES),
    }
    write_glb(output, document, binary)
    update_manifests(output)
    print(f"Expanded master: {output}")
    print(f"Core actions preserved: {len(sources)}")
    print(f"Composite actions added: {len(RECIPES)}")
    print(f"Total actions: {len(document['animations'])}")
    print(f"SHA-256: {hashlib.sha256(output.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
