"""Read-only GLB track/skeleton checks; NOT anatomical or linguistic validation.

No Blender, IK, retargeting, mesh changes or new motion is produced. Uses only
stdlib to inspect this master GLB's LINEAR quaternion animation tracks.
"""

import bisect
import json
import math
import struct
from pathlib import Path

MASTER = (
    Path(__file__).resolve().parents[2]
    / "frontend/public/models/louise_signs_master.glb"
)


def read_glb(path):
    data = path.read_bytes()
    magic, version, size = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or size != len(data):
        raise ValueError("Invalid GLB header")
    length, kind = struct.unpack_from("<II", data, 12)
    if kind != 0x4E4F534A:
        raise ValueError("Missing JSON chunk")
    document = json.loads(data[20 : 20 + length])
    offset = 20 + length
    binary_length, binary_kind = struct.unpack_from("<II", data, offset)
    if binary_kind != 0x004E4942:
        raise ValueError("Missing BIN chunk")
    return document, data[offset + 8 : offset + 8 + binary_length]


def accessor(document, binary, index):
    access = document["accessors"][index]
    if access["componentType"] != 5126 or "sparse" in access:
        raise ValueError("Unsupported accessor format")
    count = {"SCALAR": 1, "VEC4": 4}[access["type"]]
    view = document["bufferViews"][access["bufferView"]]
    stride = view.get("byteStride", count * 4)
    offset = view.get("byteOffset", 0) + access.get("byteOffset", 0)
    return [
        struct.unpack_from("<" + "f" * count, binary, offset + i * stride)
        for i in range(access["count"])
    ]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


def slerp(a, b, ratio):
    cosine = dot(a, b)
    if cosine < 0:
        b = [-value for value in b]
        cosine = -cosine
    if cosine > 0.9995:
        value = [(1 - ratio) * x + ratio * y for x, y in zip(a, b, strict=True)]
        norm = math.sqrt(dot(value, value))
        return [x / norm for x in value]
    angle = math.acos(max(-1, min(1, cosine)))
    return [
        (math.sin((1 - ratio) * angle) * x + math.sin(ratio * angle) * y)
        / math.sin(angle)
        for x, y in zip(a, b, strict=True)
    ]


def matrix(node, rotation):
    x, y, z, w = rotation
    rotation_rows = [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]
    scale = node.get("scale", [1, 1, 1])
    translate = node.get("translation", [0, 0, 0])
    return [
        [rotation_rows[i][j] * scale[j] for j in range(3)] + [translate[i]]
        for i in range(3)
    ] + [[0, 0, 0, 1]]


def multiply(a, b):
    return [
        [sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)
    ]


def audit(path=MASTER):
    document, binary = read_glb(path)
    nodes = document["nodes"]
    parents = {
        child: index
        for index, node in enumerate(nodes)
        for child in node.get("children", [])
    }
    names = {node.get("name", ""): index for index, node in enumerate(nodes)}
    errors = []
    reports = []
    neutral = {}
    all_tracks = {}
    for animation in document["animations"]:
        tracks = {}
        for channel in animation["channels"]:
            if channel["target"]["path"] != "rotation":
                errors.append(f"{animation['name']}: unexpected non-rotation channel")
                continue
            sampler = animation["samplers"][channel["sampler"]]
            if sampler.get("interpolation", "LINEAR") != "LINEAR":
                raise ValueError("Audit only supports LINEAR quaternion tracks")
            times = [t[0] for t in accessor(document, binary, sampler["input"])]
            values = accessor(document, binary, sampler["output"])
            if len(times) != len(values) or any(
                b <= a for a, b in zip(times, times[1:])
            ):
                errors.append(f"{animation['name']}: invalid keyframe timing")
            if any(not math.isfinite(v) for row in values for v in row) or any(
                abs(dot(q, q) - 1) > 0.001 for q in values
            ):
                errors.append(f"{animation['name']}: non-finite/non-unit quaternion")
            tracks[channel["target"]["node"]] = (times, values)
        all_tracks[animation["name"]] = tracks
        if animation["name"] == "IDLE":
            neutral = {i: track[1][0] for i, track in tracks.items()}
    for name, tracks in all_tracks.items():
        times = sorted({t for track in tracks.values() for t in track[0]})
        samples = sorted(set(times + [(a + b) / 2 for a, b in zip(times, times[1:])]))
        lengths = {side: [] for side in ("Left", "Right")}
        max_bend = 0
        max_wrist_swing = 0
        max_upper_elevation = 0
        max_rotation_speed = 0
        min_margin = float("inf")
        for node, (_, rotations) in tracks.items():
            if node in neutral and any(
                abs(dot(neutral[node], q)) < 0.999
                for q in (rotations[0], rotations[-1])
            ):
                errors.append(
                    f"{name}: neutral endpoint mismatch on {nodes[node].get('name')}"
                )
            if nodes[node].get("name", "").endswith(("Arm", "Hand")):
                keys, values = tracks[node]
                for a, b, qa, qb in zip(keys, keys[1:], values, values[1:]):
                    if b - a > 1e-5:
                        cosine = abs(dot(qa, qb)) / math.sqrt(dot(qa, qa) * dot(qb, qb))
                        max_rotation_speed = max(
                            max_rotation_speed,
                            math.degrees(2 * math.acos(min(1, cosine))) / (b - a),
                        )
        for time in samples:
            rotations = {}
            for index, (keys, values) in tracks.items():
                right = bisect.bisect_right(keys, time)
                if right == 0:
                    rotations[index] = values[0]
                elif right == len(keys):
                    rotations[index] = values[-1]
                else:
                    rotations[index] = slerp(
                        values[right - 1],
                        values[right],
                        (time - keys[right - 1]) / (keys[right] - keys[right - 1]),
                    )
            world = {}

            def transform(index):
                if index not in world:
                    local = matrix(
                        nodes[index],
                        rotations.get(
                            index, nodes[index].get("rotation", [0, 0, 0, 1])
                        ),
                    )
                    world[index] = (
                        multiply(transform(parents[index]), local)
                        if index in parents
                        else local
                    )
                return world[index]

            for side in ("Left", "Right"):
                points = [
                    [
                        transform(names[f"mixamorig8:{side}{part}"])[i][3]
                        for i in range(3)
                    ]
                    for part in ("Arm", "ForeArm", "Hand")
                ]
                shoulder, elbow, wrist = points
                u = [s - e for s, e in zip(shoulder, elbow, strict=True)]
                v = [w - e for w, e in zip(wrist, elbow, strict=True)]
                upper, lower = math.sqrt(dot(u, u)), math.sqrt(dot(v, v))
                max_upper_elevation = max(
                    max_upper_elevation,
                    math.degrees(math.acos(max(-1, min(1, u[1] / upper)))),
                )
                hand_node = names[f"mixamorig8:{side}Hand"]
                wrist = rotations.get(
                    hand_node, nodes[hand_node].get("rotation", [0, 0, 0, 1])
                )
                axis = nodes[hand_node]["translation"]
                axis = [v / math.sqrt(dot(axis, axis)) for v in axis]
                projection = dot(wrist[:3], axis)
                swing = math.degrees(
                    2
                    * math.acos(
                        min(
                            1,
                            math.sqrt(
                                (wrist[3] ** 2 + projection**2) / dot(wrist, wrist)
                            ),
                        )
                    )
                )
                max_wrist_swing = max(max_wrist_swing, swing)
                lengths[side].append((upper, lower))
                bend = 180 - math.degrees(
                    math.acos(max(-1, min(1, dot(u, v) / (upper * lower))))
                )
                max_bend = max(max_bend, bend)
                min_margin = min(min_margin, abs(elbow[0]) - abs(shoulder[0]))
        max_length_drift = max(
            max(row[i] for row in values) - min(row[i] for row in values)
            for values in lengths.values()
            for i in (0, 1)
        )
        if max_length_drift > 0.001:
            errors.append(f"{name}: arm segment length drift exceeds 1mm")
        if max_bend > 165:
            errors.append(f"{name}: sampled elbow bend exceeds 165 degrees")
        if document.get("extras", {}).get("arm_roll_repair"):
            if max_bend > 140:
                errors.append(f"{name}: repaired elbow bend exceeds review bound")
            if max_wrist_swing > 45.1:
                errors.append(f"{name}: repaired wrist swing exceeds 45 degrees")
            if max_rotation_speed > 161:
                errors.append(
                    f"{name}: repaired arm rotation exceeds 160 degrees/second"
                )
        reports.append(
            {
                "action": name,
                "samples": len(samples),
                "duration_seconds": round(times[-1], 3),
                "max_elbow_bend_degrees": round(max_bend, 2),
                "max_wrist_swing_degrees": round(max_wrist_swing, 2),
                "max_upper_arm_elevation_degrees": round(max_upper_elevation, 2),
                "max_arm_rotation_degrees_per_second": round(max_rotation_speed, 2),
                "min_outward_margin_m": round(min_margin, 4),
                "max_arm_length_drift_m": round(max_length_drift, 8),
            }
        )
    return {
        "asset": str(path),
        "errors": errors,
        "actions": reports,
        "limitations": "Samples keyframes and midpoint slerps only. Does not validate skinning, collisions, fingers, facial grammar or any sign language.",
    }


if __name__ == "__main__":
    report = audit()
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(report["errors"]))
