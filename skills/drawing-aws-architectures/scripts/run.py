"""Entry point: python scripts/run.py <command>. Works with `python -I` (adds its own folder to sys.path)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from awsdraw.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
