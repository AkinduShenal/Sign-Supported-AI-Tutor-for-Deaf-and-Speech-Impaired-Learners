"""JSON task export -> group holdout report and a fresh local artifact bundle."""

import argparse
import json
from pathlib import Path

from .artifacts import save_artifact
from .training import train


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="Local UTF-8 JSON array of task records",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New artifact directory; must not exist",
    )
    parser.add_argument(
        "--provenance", required=True, help="Audited export/source description"
    )
    parser.add_argument(
        "--data-kind",
        choices=["synthetic_development", "real_collected"],
        required=True,
    )
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.25)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError(
                f"Artifact directory already exists: {args.output}; choose a new output"
            )
        rows = json.loads(args.dataset.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError("Dataset must be a JSON array of task records")
        run = train(
            rows,
            provenance=args.provenance,
            data_kind=args.data_kind,
            random_state=args.random_state,
            test_size=args.test_size,
        )
        save_artifact(run, args.output)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Offline training failed: {error}\n")
    print(json.dumps(run.metadata, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
