"""CLI: python -m healthsafe_pipeline [--source path/to/wards.csv]"""
import argparse
import logging
import sys
from pathlib import Path

from . import pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the HealthSafe data pipeline.")
    parser.add_argument("--source", type=Path, help="CSV to ingest (default: data/wards-outdated.csv)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    try:
        pipeline.run(source=args.source)
    except Exception:
        logging.getLogger("healthsafe_pipeline").exception("pipeline failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
