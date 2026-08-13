#!/usr/bin/env python3
"""Entry point: python main.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from sprint_planning_automator.cli import main

if __name__ == "__main__":
    main()
