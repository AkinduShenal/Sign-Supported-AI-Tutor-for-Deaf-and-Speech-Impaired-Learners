"""Generate a reproducible SYNTHETIC_ENGINEERING_DEMO_ONLY training fixture.

Run from backend/: python -m scripts.generate_quiz_dynamic_synthetic
This reads the checked-in 60-question bank and calls the production dynamic
feature extractor for every simulated ten-question session. It opens no DB,
imports no application settings, uses no network and trains no model.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from app.modules.quiz.dynamic_ml_features import (
    FEATURE_NAMES, FEATURE_SCHEMA_VERSION, SLOT_BLUEPRINT,
    SUPPORTED_BANK_VERSION, extract_dynamic_features,
)
from scripts.generate_quiz_dynamic_bank import build_bank
from scripts.seed_quiz_dynamic import load_bank


DATA_ORIGIN = "SYNTHETIC_ENGINEERING_DEMO_ONLY"
TARGET_NAMES = ("target_M1", "target_M2", "target_M3", "target_M4")
CSV_NAME = "quiz_dynamic_synthetic_training_v1.csv"
CONTRACT_NAME = "quiz_dynamic_feature_contract_v1.json"
DEFAULT_SEED = 20261022
DEFAULT_ROWS = 2400

# Deliberately proposed simulation assumptions, not teacher-confirmed labels.
# A misconception can influence several slots; no option tag defines a target.
SLOT_EFFECTS = {
    "M1": {"S01": 0.95, "S03": 0.75, "S04": 0.75, "S05": 0.45,
           "S07": 0.45, "S08": 0.55},
    "M2": {"S05": 0.60, "S06": 0.60, "S07": 0.60, "S08": 0.60,
           "S09": 1.25, "S10": 0.35},
    "M3": {"S02": 1.15, "S06": 0.65, "S09": 0.75, "S10": 0.85},
    "M4": {"S03": 1.00, "S04": 1.10, "S05": 0.45, "S06": 0.45,
           "S07": 0.45, "S08": 0.50, "S10": 0.60},
}
TIER_LOGIT = {"easy": 1.35, "medium": 0.60, "hard": -0.05}
TIER_TIME_SEC = {"easy": 15.0, "medium": 23.0, "hard": 32.0}
TAG_WEIGHTS = {"inverse_operation": ("M1", 3.0),
               "sign_error": ("M3", 3.0),
               "arithmetic_error": ("M4", 1.8),
               "concept_confusion": ("M2", 1.2)}


@dataclass(frozen=True)
class SyntheticProfile:
    """Latent synthetic targets are assigned before any answer is simulated."""

    learner_id: str
    targets: tuple[int, int, int, int]
    ability: float
    speed_factor: float
    confidence_bias: float

    def active(self, category: str) -> bool:
        return bool(self.targets[int(category[1]) - 1])


def _profiles(count: int, rng: random.Random) -> list[SyntheticProfile]:
    if count < 96 or count % 16:
        raise ValueError("Row count must be at least 96 and divisible by 16")
    combinations = [tuple((bits >> bit) & 1 for bit in range(4))
                    for bits in range(16)] * (count // 16)
    rng.shuffle(combinations)
    return [SyntheticProfile(
        learner_id=f"SYN-{index:06d}",
        targets=targets,
        ability=rng.normalvariate(0, 0.48),
        speed_factor=rng.lognormvariate(0, 0.22),
        confidence_bias=rng.normalvariate(0, 0.30),
    ) for index, targets in enumerate(combinations, 1)]


def _choose_answer(question: dict, profile: SyntheticProfile,
                   previous_wrong: bool, rng: random.Random) -> tuple[dict, float, str]:
    slot = question["logical_slot"]
    tier = question["difficulty_level"]
    penalty = sum(SLOT_EFFECTS[category].get(slot, 0)
                  for category in SLOT_EFFECTS if profile.active(category))
    # Correct answers remain possible for every profile and wrong answers can
    # occur with no active misconception. Variant noise is independent of label.
    logit = (TIER_LOGIT[tier] + profile.ability - penalty
             - (0.16 if previous_wrong else 0) + rng.normalvariate(0, 0.15))
    p_correct = max(0.07, min(0.96, 1 / (1 + math.exp(-logit))))
    correct = rng.random() < p_correct
    if correct:
        chosen = next(option for option in question["options"] if option["is_correct"])
    else:
        wrong = [option for option in question["options"] if not option["is_correct"]]
        weights = []
        for option in wrong:
            weight = 1.0
            association = TAG_WEIGHTS.get(option["misconception_code"])
            if association and profile.active(association[0]):
                # Heuristic option preference only. M2 has no matching bank tag;
                # M4's arithmetic tag is broad and is not an M4 label.
                weight += association[1] * (1 + SLOT_EFFECTS[association[0]].get(slot, 0))
            weights.append(weight)
        chosen = rng.choices(wrong, weights=weights, k=1)[0]

    time_scale = 0.88 if not correct and penalty > 0 else 1.0
    seconds = round(max(2.0, min(100.0,
        TIER_TIME_SEC[tier] * profile.speed_factor * time_scale
        * rng.lognormvariate(0, 0.29))), 3)
    confidence_signal = (
        0.40 * profile.ability + profile.confidence_bias
        + (0.85 if correct else -0.15)
        + (0.55 if not correct and penalty > 0 else 0)
        + rng.normalvariate(0, 0.48)
    )
    confidence = "low" if confidence_signal < -0.15 else (
        "medium" if confidence_signal < 0.78 else "high")
    return chosen, seconds, confidence


def _simulate_session(index: int, profile: SyntheticProfile,
                      by_slot: dict[str, list[dict]], rng: random.Random) -> tuple[dict, list[str]]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=index * 15)
    session_id = f"SYNTH-QUIZ-{index:06d}"
    selections, questions, responses, options = [], [], [], []
    variant_codes = []
    elapsed = 0.0
    previous_wrong = False
    for order, slot in enumerate(SLOT_BLUEPRINT, 1):
        # Balanced deterministic coverage: each slot sees all six variants,
        # and a session contains a mixture of variant numbers.
        item = by_slot[slot][(index - 1 + 5 * (order - 1)) % 6]
        question_id = item["question_code"]
        variant_codes.append(question_id)
        selected, seconds, confidence = _choose_answer(item, profile, previous_wrong, rng)
        elapsed += seconds + 1.5
        selections.append(SimpleNamespace(quiz_session_id=session_id,
                                          question_order=order, question_id=question_id))
        questions.append(SimpleNamespace(
            id=question_id, question_code=question_id, bank_version=item["bank_version"],
            logical_slot=slot, concept_id=item["concept_id"],
            subconcept_code=item["subconcept_code"],
            difficulty_level=item["difficulty_level"],
            question_type="multiple_choice", assessment_use="pre"))
        for option in item["options"]:
            options.append(SimpleNamespace(
                id=f"{question_id}:{option['option_code']}", question_id=question_id,
                option_code=option["option_code"], is_correct=option["is_correct"],
                misconception_code=option["misconception_code"]))
        responses.append(SimpleNamespace(
            quiz_session_id=session_id, question_id=question_id, question_order=order,
            selected_option_id=f"{question_id}:{selected['option_code']}",
            is_correct=selected["is_correct"],
            misconception_code=selected["misconception_code"],
            response_time_sec=seconds, confidence_level=confidence,
            answered_at=start + timedelta(seconds=elapsed)))
        previous_wrong = not selected["is_correct"]
    session = SimpleNamespace(
        quiz_session_id=session_id, student_id=profile.learner_id,
        bank_version=SUPPORTED_BANK_VERSION, concept_id="linear_equations",
        assessment_phase="pre_tutor", status="completed", started_at=start,
        completed_at=start + timedelta(seconds=elapsed + 1))
    vector = extract_dynamic_features(session, selections, questions, responses, options)
    return vector, variant_codes


def build_dataset(count: int = DEFAULT_ROWS, seed: int = DEFAULT_SEED) -> tuple[list[dict], dict]:
    """Build rows entirely in memory; no DB or output file is touched."""
    rng = random.Random(seed)
    bank = load_bank()
    if bank != build_bank():
        raise ValueError("Draft bank differs from its reproducible mathematical blueprint")
    by_slot = defaultdict(list)
    for question in bank:
        expected_skill, expected_tier = SLOT_BLUEPRINT[question["logical_slot"]]
        if (question["bank_version"] != SUPPORTED_BANK_VERSION or
                question["subconcept_code"] != expected_skill or
                question["difficulty_level"] != expected_tier):
            raise ValueError("Bank disagrees with the versioned feature blueprint")
        by_slot[question["logical_slot"]].append(question)
    if set(by_slot) != set(SLOT_BLUEPRINT):
        raise ValueError("Bank slot coverage is incomplete")
    for items in by_slot.values():
        items.sort(key=lambda item: item["question_code"])
        if len(items) != 6:
            raise ValueError("Expected six variants per slot")

    rows = []
    coverage = Counter()
    profile_counts = Counter()
    for index, profile in enumerate(_profiles(count, rng), 1):
        vector, variants = _simulate_session(index, profile, by_slot, rng)
        coverage.update(variants)
        profile_counts[profile.targets] += 1
        values = vector["features"]
        if (tuple(values) != FEATURE_NAMES or len(values) != 62 or
                any(not math.isfinite(value) for value in values.values()) or
                values["correct_count"] + values["incorrect_count"] != 10 or
                sum(values[f"confidence_{level}_count"] for level in
                    ("low", "medium", "high")) != 10 or
                sum(values[f"option_{tag}_count"] for tag in
                    ("inverse_operation", "sign_error", "arithmetic_error", "concept_confusion"))
                    != values["incorrect_count"]):
            raise ValueError("Simulated feature row failed consistency checks")
        rows.append({
            **values,
            **dict(zip(TARGET_NAMES, profile.targets)),
            "learner_id": profile.learner_id,
            "data_origin": DATA_ORIGIN,
            "bank_version": vector["bank_version"],
            "feature_schema_version": vector["feature_schema_version"],
        })
    if (set(coverage) != {q["question_code"] for q in bank} or
            max(coverage.values()) - min(coverage.values()) > 1):
        raise ValueError("All 60 variants must have balanced coverage")
    if (set(profile_counts) != {tuple((bits >> bit) & 1 for bit in range(4))
                                for bits in range(16)} or
            len(set(profile_counts.values())) != 1):
        raise ValueError("All sixteen synthetic target profiles must be balanced")
    return rows, {"coverage": coverage, "profiles": profile_counts}


def write_outputs(output_dir: Path, rows: list[dict]) -> tuple[Path, Path]:
    """Write only inside workspace tmp and refuse to overwrite existing files."""
    workspace_tmp = (Path(__file__).resolve().parents[2] / "tmp").resolve()
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(workspace_tmp):
        raise ValueError(f"Output directory must be under {workspace_tmp}")
    csv_path, json_path = output_dir / CSV_NAME, output_dir / CONTRACT_NAME
    if csv_path.exists() or json_path.exists():
        raise FileExistsError("Output exists; choose a new directory to preserve it")
    output_dir.mkdir(parents=True, exist_ok=True)
    columns = list(FEATURE_NAMES) + list(TARGET_NAMES) + [
        "learner_id", "data_origin", "bank_version", "feature_schema_version"]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    contract = {
        "feature_names": list(FEATURE_NAMES),
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "bank_version": SUPPORTED_BANK_VERSION,
    }
    csv_path.write_text(buffer.getvalue(), encoding="utf-8", newline="")
    json_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return csv_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output-dir", type=Path, default=(
        Path(__file__).resolve().parents[2] / "tmp" / "quiz_dynamic_ml_demo"))
    args = parser.parse_args()
    rows, report = build_dataset(args.rows, args.seed)
    csv_path, json_path = write_outputs(args.output_dir, rows)
    print(f"Generated {len(rows)} synthetic-only sessions; all 60 variants covered")
    print(f"Sixteen profile combinations: {len(report['profiles'])}; seed: {args.seed}")
    print(csv_path)
    print(json_path)


if __name__ == "__main__":
    main()
