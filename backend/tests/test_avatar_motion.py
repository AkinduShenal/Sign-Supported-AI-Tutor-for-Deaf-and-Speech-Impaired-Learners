"""Asset-level regressions: these checks do NOT validate a sign language."""

import hashlib
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "avatar-sign-package/tools"))
from audit_master_motion import audit, read_glb, dot, matrix, multiply  # noqa: E402
from repair_master_arm_roll import Rig, angle, repair_file  # noqa: E402

MASTER = ROOT / "frontend/public/models/louise_signs_master.glb"


@pytest.fixture(scope="module")
def rig():
    return Rig(*read_glb(MASTER))


def test_canonical_master_and_validation_policy(rig):
    manifest = json.loads(
        (ROOT / "avatar-sign-package/manifest/signs.json").read_text()
    )
    assert (
        hashlib.sha256(MASTER.read_bytes()).hexdigest()
        == manifest["master_avatar_sha256"]
    )
    assert len(rig.tracks) == 56
    assert rig.doc["extras"]["composite_prototype_expansion"] == {
        "language_validation": "none",
        "review_required": True,
        "core_actions_preserved": 22,
        "composite_actions_added": 34,
    }
    assert rig.doc["extras"]["arm_roll_repair"]["language_validation"] == "none"
    for sign in manifest["signs"]:
        if sign["id"] in rig.tracks and sign["id"] != "IDLE":
            assert sign["validation_status"] != "validated"


def test_full_motion_limits_and_consistent_neutral():
    report = audit(MASTER)
    assert report["errors"] == []
    for action in report["actions"]:
        assert action["max_wrist_swing_degrees"] <= 45.1
        assert action["max_upper_arm_elevation_degrees"] < 36
        # Asset regression bound, not a medical/anatomical validity claim.
        assert action["max_elbow_bend_degrees"] < 140
        assert action["max_arm_rotation_degrees_per_second"] <= 161


def test_every_manifest_action_has_a_master_track(rig):
    manifest = json.loads(
        (ROOT / "avatar-sign-package/manifest/signs.json").read_text()
    )
    assert {sign["id"] for sign in manifest["signs"]} == set(rig.tracks)


def test_no_duplicate_float32_times_and_unit_rotations(rig):
    for tracks in rig.tracks.values():
        for times, values in tracks.values():
            assert len(times) == len(values)
            assert all(b > a for a, b in zip(times, times[1:]))
            assert all(math.isfinite(v) for q in values for v in q)
            assert all(abs(dot(q, q) - 1) < 1e-5 for q in values)


def test_hands_stay_in_front_of_the_torso_during_transitions(rig):
    # Conservative rig-space clearance, not a mesh collision/skin validity test.
    for name, tracks in rig.tracks.items():
        duration = max(times[-1] for times, _ in tracks.values())
        for frame in range(121):
            pose = rig.pose(name, duration * frame / 120)
            world = {}

            def transform(i):
                if i not in world:
                    node = rig.nodes[i]
                    local = matrix(
                        node, pose.get(i, node.get("rotation", [0, 0, 0, 1]))
                    )
                    world[i] = (
                        multiply(transform(rig.parents[i]), local)
                        if i in rig.parents
                        else local
                    )
                return world[i]

            for side in ("Left", "Right"):
                hand = transform(rig.names[f"mixamorig8:{side}Hand"])
                x, y, z = [hand[i][3] for i in range(3)]
                assert abs(x) < 0.4, (name, frame, side, "out of frame", x)
                if y > 1.05:
                    assert z > 0.06, (name, frame, side, "hand behind torso plane", z)


def test_number_actions_keep_distinct_existing_finger_shapes(rig):
    nodes = [
        i
        for i, n in enumerate(rig.nodes)
        if "RightHand" in n.get("name", "") and n["name"].endswith(("1", "2", "3"))
    ]
    poses = []
    for number in range(6):
        action = next(
            a for a in rig.doc["animations"] if a["name"] == f"NUMBER_{number}"
        )
        poses.append(
            rig.pose(action["name"], action["extras"]["posture_repair"]["key_times"][2])
        )
    for a, b in zip(poses, poses[1:]):
        assert any(angle(a[i], b[i]) > 1 for i in nodes)


def test_repair_refuses_unknown_assets_or_overwriting_source(tmp_path):
    with pytest.raises(ValueError, match="never overwrite"):
        repair_file(MASTER, MASTER)
    with pytest.raises(ValueError, match="Unexpected source"):
        repair_file(MASTER, tmp_path / "must-not-exist.glb")
    assert not (tmp_path / "must-not-exist.glb").exists()
