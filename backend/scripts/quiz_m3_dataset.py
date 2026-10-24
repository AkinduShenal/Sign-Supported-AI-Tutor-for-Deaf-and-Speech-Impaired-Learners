"""Offline M3-A Quiz feature and independent-label validator; no database access.

From backend/: python -m scripts.quiz_m3_dataset --help
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.modules.quiz.research_m3.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in (
        "quiz-sessions",
        "quiz-responses",
        "taxonomy",
        "items",
        "assessments",
        "evidence",
        "labels",
    ):
        parser.add_argument(
            f"--{flag}", type=Path, required=True, help="Explicit local CSV path"
        )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Fresh directory; never overwritten",
    )
    args = parser.parse_args()
    try:
        report = run_pipeline(
            {
                "quiz_sessions": args.quiz_sessions,
                "quiz_responses": args.quiz_responses,
                "taxonomy": args.taxonomy,
                "items": args.items,
                "assessments": args.assessments,
                "evidence": args.evidence,
                "labels": args.labels,
            },
            args.output_dir,
        )
    except (ValueError, OSError) as error:
        parser.exit(2, f"M3-A validation stopped: {error}\n")
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir.resolve()),
                "readiness": report["readiness"],
                "valid_quiz_feature_rows": report["valid_quiz_feature_rows"],
                "eligible_training_records": report["eligible_training_records"],
                "quarantined_assessment_count": report["quarantined_assessment_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
