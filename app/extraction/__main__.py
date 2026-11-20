"""Run the standalone extractor on a UTF-8 text file."""

import argparse
import sys
from pathlib import Path

import httpx

from .extractor import extract_cv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="A UTF-8 file containing the raw text of one CV")
    args = parser.parse_args()
    try:
        cv = extract_cv(args.file.read_text(encoding="utf-8-sig"))
    except (OSError, RuntimeError, ValueError, httpx.HTTPError) as error:
        parser.exit(1, f"Extraction failed. {error}\n")
    sys.stdout.buffer.write((cv.model_dump_json(indent=2) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
