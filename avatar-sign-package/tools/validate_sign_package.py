import hashlib
import json
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
MANIFEST_PATH = ROOT / "manifest" / "signs.json"
PHRASE_MAP_PATH = ROOT / "manifest" / "phrase_map.json"
MASTER_GLB_PATH = (
    REPOSITORY_ROOT / "frontend" / "public" / "models" / "louise_signs_master.glb"
)
ALLOWED_STATUSES = {"needs_validation", "validated", "technical_only"}

manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
phrase_map = json.loads(PHRASE_MAP_PATH.read_text(encoding="utf-8"))
errors: list[str] = []
missing: list[str] = []


def read_glb_animation_names(path: Path) -> set[str]:
    with path.open("rb") as glb:
        magic, version, declared_size = struct.unpack("<4sII", glb.read(12))
        if magic != b"glTF" or version != 2 or declared_size != path.stat().st_size:
            raise ValueError("Master avatar is not a valid GLB 2.0 file.")
        json_length, json_chunk_type = struct.unpack("<II", glb.read(8))
        if json_chunk_type != 0x4E4F534A:
            raise ValueError("Master avatar does not start with a JSON chunk.")
        document = json.loads(glb.read(json_length))
    return {
        animation.get("name", "")
        for animation in document.get("animations", [])
        if animation.get("name")
    }

ids = [sign["id"] for sign in manifest["signs"]]
id_set = set(ids)
if len(ids) != len(id_set):
    errors.append("Duplicate sign IDs found.")

for sign in manifest["signs"]:
    if sign["validation_status"] not in ALLOWED_STATUSES:
        errors.append(
            f"{sign['id']} has invalid status {sign['validation_status']!r}."
        )

    clip = ROOT / sign["clip"]
    if not clip.exists():
        missing.append(sign["id"])
        if sign["validation_status"] == "validated":
            errors.append(f"Validated clip file is missing: {sign['id']}.")

if MASTER_GLB_PATH.exists():
    actual_sha256 = hashlib.sha256(MASTER_GLB_PATH.read_bytes()).hexdigest()
    expected_sha256 = manifest.get("master_avatar_sha256")
    if expected_sha256 and actual_sha256 != expected_sha256:
        errors.append("Master GLB checksum does not match the manifest.")

    try:
        master_actions = read_glb_animation_names(MASTER_GLB_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        master_actions = set()
        errors.append(str(error))

    for sign in manifest["signs"]:
        if not sign.get("prototype_ready"):
            continue
        animation_action = sign.get("animation_action")
        if not animation_action:
            errors.append(
                f"Prototype-ready entry has no animation action: {sign['id']}."
            )
        elif animation_action not in master_actions:
            errors.append(
                f"Prototype action is missing from master GLB: {animation_action}."
            )
else:
    master_actions = set()

referenced_ids = {
    action
    for rule in phrase_map["rules"]
    for action in rule["actions"]
}
referenced_ids.update(phrase_map["expression_tokens"].values())
for unknown_id in sorted(referenced_ids - id_set):
    errors.append(f"Phrase map references unknown sign ID: {unknown_id}.")

print(f"Signs in manifest: {len(ids)}")
print(
    "Validated lexical signs: "
    f"{sum(sign['validation_status'] == 'validated' for sign in manifest['signs'])}"
)
print(f"Prototype-ready educational gestures: {len(master_actions)}")
print(f"Missing standalone source clips: {len(missing)}")

if MASTER_GLB_PATH.exists():
    print(f"Master GLB: FOUND ({MASTER_GLB_PATH})")
else:
    print(f"Master GLB: MISSING ({MASTER_GLB_PATH})")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    sys.exit(1)

print("Manifest and phrase-map structure: OK")
print(
    "NOTE: Prototype educational gestures are playable but are not validated "
    "Sri Lankan Sign Language signs."
)
