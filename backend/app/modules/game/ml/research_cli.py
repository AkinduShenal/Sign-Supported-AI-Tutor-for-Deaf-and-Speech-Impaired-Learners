"""Local audited research observations + configuration -> paired offline report."""

import argparse
import json
from pathlib import Path

from .research_artifacts import save_comparison
from .research_training import ExperimentConfig, run_comparison


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="JSON array of learner–concept–assessment observations",
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Research experiment JSON configuration",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New paired artifact directory; must not exist",
    )
    parser.add_argument("--provenance", required=True)
    parser.add_argument(
        "--data-kind",
        choices=["synthetic_development", "real_collected"],
        required=True,
    )
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError(f"Artifact directory already exists: {args.output}")
        rows = json.loads(args.dataset.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError("Research dataset must be a JSON array")
        config = ExperimentConfig.model_validate_json(
            args.config.read_text(encoding="utf-8")
        )
        comparison = run_comparison(
            rows, config, provenance=args.provenance, data_kind=args.data_kind
        )
        save_comparison(comparison, args.output)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Offline research comparison failed: {error}\n")
    print(json.dumps(comparison.report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
