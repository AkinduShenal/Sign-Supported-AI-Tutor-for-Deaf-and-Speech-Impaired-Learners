import json
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
print(f"Missing clip files: {len(missing)}")
for sign_id in missing:
    print(f"  MISSING: {sign_id}")

if MASTER_GLB_PATH.exists():
    print(f"Master GLB: FOUND ({MASTER_GLB_PATH})")
else:
    print(f"Master GLB: MISSING ({MASTER_GLB_PATH})")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    sys.exit(1)

print("Manifest and phrase-map structure: OK")
print("NOTE: Missing unvalidated clips are expected until reviewed assets are added.")
