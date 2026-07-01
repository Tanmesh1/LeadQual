import argparse
import asyncio
from pathlib import Path

from app.automation.indiamart.extractor import run_from_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract IndiaMART buy leads with Playwright.")
    parser.add_argument(
        "--selectors",
        type=Path,
        default=None,
        help="Path to the IndiaMART selector JSON file.",
    )
    args = parser.parse_args()
    asyncio.run(run_from_settings(args.selectors))


if __name__ == "__main__":
    main()
