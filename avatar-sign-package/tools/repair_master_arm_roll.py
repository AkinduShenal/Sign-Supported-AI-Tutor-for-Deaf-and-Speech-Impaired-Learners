"""Repair the supplied prototype's arm roll, not generate sign-language motion.

Corrective FK on the existing prototype: lower flared upper arms, raise the
forearms into a chest-level presentation space, remove wrist roll and limit
wrist swing. This DOES change arm paths/palm orientations, so is not a linguistic
repair. Finger key poses and static body channels are preserved; moving tracks
are eased and retimed together. No IK targets or sign
templates are created. Input is pinned; output must be a separate review file.
"""

import argparse
import bisect
import hashlib
import json
import math
import struct
from pathlib import Path

from audit_master_motion import accessor, dot, read_glb, slerp

SOURCE_SHA = "31fd3bbd41cf1cac8c808becd9fd285ba605e3981c721c5a4f1c822b4861b24e"


def normalize(v):
    length = math.sqrt(dot(v, v))
    if length < 1e-10:
        raise ValueError("Cannot normalize a zero vector")
    return [x / length for x in v]


def cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def qm(a, b):
    x, y, z, w = a
    X, Y, Z, W = b
    return [
        w * X + x * W + y * Z - z * Y,
        w * Y - x * Z + y * W + z * X,
        w * Z + x * Y - y * X + z * W,
        w * W - x * X - y * Y - z * Z,
    ]


def inv(q):
    return [-q[0], -q[1], -q[2], q[3]]


def rotate(q, v):
    return qm(qm(q, [*v, 0]), inv(q))[:3]


def between(a, b):
    a, b = normalize(a), normalize(b)
    d = dot(a, b)
    if d < -0.999999:
        axis = cross(a, [1, 0, 0] if abs(a[0]) < 0.9 else [0, 0, 1])
        return [*normalize(axis), 0]
    return normalize([*cross(a, b), 1 + d])


def angle(a, b):
    return math.degrees(2 * math.acos(min(1, abs(dot(normalize(a), normalize(b))))))


class Rig:
    def __init__(self, doc, binary):
        self.doc, self.binary = doc, binary
        self.nodes = doc["nodes"]
        self.names = {node.get("name"): i for i, node in enumerate(self.nodes)}
        self.parents = {
            c: i for i, n in enumerate(self.nodes) for c in n.get("children", [])
        }
        self.tracks = {}
        for animation in doc["animations"]:
            tracks = {}
            for channel in animation["channels"]:
                sampler = animation["samplers"][channel["sampler"]]
                if (
                    channel["target"]["path"] != "rotation"
                    or sampler.get("interpolation", "LINEAR") != "LINEAR"
                ):
                    raise ValueError(
                        "This repair is only for the supplied rotation-only prototype"
                    )
                tracks[channel["target"]["node"]] = (
                    [row[0] for row in accessor(doc, binary, sampler["input"])],
                    accessor(doc, binary, sampler["output"]),
                )
            self.tracks[animation["name"]] = tracks
        self.rest_world = self.world({})
        self.neutral_world = self.world(self.pose("IDLE", 0))

    def pose(self, name, time):
        rotations = {}
        for node, (times, values) in self.tracks[name].items():
            right = bisect.bisect_right(times, time)
            if right == 0:
                q = values[0]
            elif right == len(times):
                q = values[-1]
            else:
                q = slerp(
                    values[right - 1],
                    values[right],
                    (time - times[right - 1]) / (times[right] - times[right - 1]),
                )
            rotations[node] = normalize(q)
        return rotations

    def world(self, pose):
        world = {}

        def visit(i):
            if i not in world:
                q = normalize(pose.get(i, self.nodes[i].get("rotation", [0, 0, 0, 1])))
                world[i] = qm(visit(self.parents[i]), q) if i in self.parents else q
            return world[i]

        for i in range(len(self.nodes)):
            visit(i)
        return world

    def repair(self, pose):
        world = self.world(pose)
        repaired = dict(pose)
        for side in ("Left", "Right"):
            arm, fore, hand = [
                self.names[f"mixamorig8:{side}{part}"]
                for part in ("Arm", "ForeArm", "Hand")
            ]
            # Their child translations define the true axes (not assumed +Y).
            upper_axis = normalize(self.nodes[fore]["translation"])
            lower_axis = normalize(self.nodes[hand]["translation"])
            upper_dir = rotate(world[arm], upper_axis)
            lower_dir = rotate(world[fore], lower_axis)
            activity = min(
                1,
                max(
                    angle(world[arm], self.neutral_world[arm]),
                    angle(world[fore], self.neutral_world[fore]),
                )
                / 40,
            )
            activity = activity * activity * (3 - 2 * activity)
            # Direct FK direction edits, not endpoint/IK solves. Keep the
            # source clip's left/right movement, but bring elbows down and
            # forearms forward/up instead of folding hands back onto sleeves.
            relaxed_upper = normalize(
                [upper_dir[0] * 0.5, -abs(upper_dir[1]) - 0.4, upper_dir[2] + 0.15]
            )
            presented_lower = normalize(
                [lower_dir[0] * 0.55, lower_dir[1] + 0.9, max(0.35, lower_dir[2])]
            )
            new_upper = normalize(
                [
                    (1 - activity) * a + activity * b
                    for a, b in zip(upper_dir, relaxed_upper)
                ]
            )
            # A shared ready/rest position keeps relaxed hands in front of the
            # waist. Returning all the way to the thighs made a few interpolated
            # paths pass through the jacket and reduced upper-body readability.
            ready_lower = normalize([0.12 if side == "Left" else -0.12, -0.5, 0.85])
            new_lower = normalize(
                [
                    (1 - activity) * a + activity * b
                    for a, b in zip(ready_lower, presented_lower)
                ]
            )
            # Transport the BIND frame, not the imported animated roll. The
            # source's right neutral arm carries a near-half-turn wrist offset;
            # retaining its upper-arm roll while moving that offset to the
            # forearm pinches the elbow skin even though all joints look valid.
            bind_direction = rotate(self.rest_world[arm], upper_axis)
            arm_start = qm(between(bind_direction, new_upper), self.rest_world[arm])
            upper_dir, lower_dir = new_upper, new_lower
            normal = cross(upper_dir, lower_dir)
            if math.sqrt(dot(normal, normal)) < 1e-5:
                continue
            normal = normalize(normal)
            # Keep a consistent bend-plane orientation. Flipping hemisphere
            # based on a per-frame dot product produces a 180-degree elbow snap.
            source_x = rotate(arm_start, [1, 0, 0])
            source_x = normalize(
                [v - dot(source_x, upper_dir) * u for v, u in zip(source_x, upper_dir)]
            )
            roll = math.atan2(
                dot(upper_dir, cross(source_x, normal)), dot(source_x, normal)
            )
            twist = [*(u * math.sin(roll / 2) for u in upper_dir), math.cos(roll / 2)]
            # Near straight arms the bend plane is ill-conditioned. Fade its
            # influence to zero at neutral instead of rolling on numerical noise.
            arm_world = slerp(arm_start, qm(twist, arm_start), activity)
            repaired[arm] = normalize(qm(inv(world[self.parents[arm]]), arm_world))
            # Transfer axial wrist roll onto the forearm, then cap the wrist
            # swing. The source has wrists folded back by up to 159 degrees.
            fore_world = qm(
                between(rotate(arm_world, lower_axis), lower_dir), arm_world
            )
            hand_local = qm(inv(fore_world), world[hand])
            projection = dot(hand_local[:3], lower_axis)
            wrist_twist = [*(v * projection for v in lower_axis), hand_local[3]]
            if dot(wrist_twist, wrist_twist) > 1e-8:
                fore_world = qm(fore_world, normalize(wrist_twist))
            repaired[fore] = normalize(qm(inv(arm_world), fore_world))
            wrist = normalize(qm(inv(fore_world), world[hand]))
            swing_degrees = angle(wrist, [0, 0, 0, 1])
            repaired[hand] = slerp(
                [0, 0, 0, 1], wrist, min(1, 45 / max(swing_degrees, 1e-9))
            )
        return repaired


def write_glb(doc, binary, path):
    doc["buffers"][0]["byteLength"] = len(binary)
    raw = json.dumps(doc, separators=(",", ":")).encode()
    raw += b" " * (-len(raw) % 4)
    binary += b"\0" * (-len(binary) % 4)
    path.write_bytes(
        struct.pack("<4sII", b"glTF", 2, 28 + len(raw) + len(binary))
        + struct.pack("<II", len(raw), 0x4E4F534A)
        + raw
        + struct.pack("<II", len(binary), 0x004E4942)
        + binary
    )


def repair_file(source, output):
    if source.resolve() == output.resolve():
        raise ValueError("Write a review candidate, never overwrite the source")
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError("Unexpected source asset; refusing to modify a different rig")
    doc, binary = read_glb(source)
    rig = Rig(doc, binary)
    binary = bytearray(binary)

    def append(rows, kind):
        binary.extend(b"\0" * (-len(binary) % 4))
        offset = len(binary)
        flat = [x for row in rows for x in row]
        binary.extend(struct.pack("<" + "f" * len(flat), *flat))
        view = len(doc["bufferViews"])
        doc["bufferViews"].append(
            {"buffer": 0, "byteOffset": offset, "byteLength": len(flat) * 4}
        )
        access = {
            "bufferView": view,
            "componentType": 5126,
            "count": len(rows),
            "type": kind,
        }
        if kind == "SCALAR":
            access.update(min=[min(flat)], max=[max(flat)])
        doc["accessors"].append(access)
        return len(doc["accessors"]) - 1

    for animation in doc["animations"]:
        name = animation["name"]
        original_times = sorted({t for ts, _ in rig.tracks[name].values() for t in ts})
        # Correct the authored KEY POSES, then ease between them. Re-solving a
        # roll frame on every in-between sample introduces near-straight elbow
        # singularities and fast flips even when endpoint pictures look fine.
        key_poses = [rig.repair(rig.pose(name, t)) for t in original_times]
        retimed = [0.0]
        for index, (start, end) in enumerate(zip(original_times, original_times[1:])):
            maximum = max(
                angle(key_poses[index][node], key_poses[index + 1][node])
                for node in key_poses[index]
            )
            # Smoothstep peaks at 1.5x its mean speed. Keep every local bone
            # under 160 deg/s at 1x; retain source holds and never rush a sign.
            interval = max(end - start, 0.65 if maximum > 1 else 0, 1.5 * maximum / 160)
            retimed.append(retimed[-1] + interval)
        retimed = [struct.unpack("<f", struct.pack("<f", t))[0] for t in retimed]
        animation.setdefault("extras", {})["posture_repair"] = {
            "source_key_times": original_times,
            "key_times": retimed,
        }
        duration = retimed[-1]
        # Quantize BEFORE deduplication: glTF stores float32. Distinct Python
        # floats can collapse into duplicate keys otherwise (e.g. t=1.50).
        times = sorted(
            {
                struct.unpack("<f", struct.pack("<f", t))[0]
                for t in retimed
                + [
                    duration * i / math.ceil(duration * 60)
                    for i in range(math.ceil(duration * 60) + 1)
                ]
            }
        )
        poses = []
        for t in times:
            right = bisect.bisect_right(retimed, t)
            if right == len(retimed):
                poses.append(key_poses[-1])
            else:
                left = max(0, right - 1)
                u = (t - retimed[left]) / (retimed[right] - retimed[left])
                u = u * u * (3 - 2 * u)
                poses.append(
                    {
                        node: slerp(key_poses[left][node], key_poses[right][node], u)
                        for node in key_poses[left]
                    }
                )
        input_index = append([[t] for t in times], "SCALAR")
        for channel in animation["channels"]:
            node = channel["target"]["node"]
            # Constant body tracks stay byte-for-byte unchanged. Easing fingers
            # along with arms preserves their synchronization and key poses.
            source_values = rig.tracks[name][node][1]
            is_arm = any(
                rig.nodes[node].get("name", "").endswith(":" + side + part)
                for side in ("Left", "Right")
                for part in ("Arm", "ForeArm", "Hand")
            )
            if not is_arm and all(
                angle(source_values[0], q) < 0.0001 for q in source_values
            ):
                continue
            values = []
            for pose in poses:
                q = pose[node]
                if values and dot(values[-1], q) < 0:
                    q = [-v for v in q]
                values.append(q)
            animation["samplers"][channel["sampler"]] = {
                "input": input_index,
                "output": append(values, "VEC4"),
                "interpolation": "LINEAR",
            }
    doc.setdefault("extras", {})["arm_roll_repair"] = {
        "source_sha256": SOURCE_SHA,
        "method": "corrective_fk_posture_and_wrist_limits",
        "language_validation": "none",
        "revision": 2,
        "wrist_swing_limit_degrees": 45,
    }
    # Imported body material had a 2x specular multiplier and a glossy texture
    # that exaggerated sleeve creases. Matte cloth/skin presentation, same mesh
    # and original colour/normal textures; no generated texture or new avatar.
    body = next(
        material for material in doc["materials"] if material["name"] == "Ch07_body"
    )
    body["pbrMetallicRoughness"].pop("metallicRoughnessTexture", None)
    body["pbrMetallicRoughness"]["roughnessFactor"] = 0.78
    specular = body["extensions"]["KHR_materials_specular"]
    specular["specularColorFactor"] = [1, 1, 1]
    specular["specularFactor"] = 0.25
    write_glb(doc, binary, output)
    return {
        "output": str(output),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(repair_file(args.source, args.output), indent=2))
