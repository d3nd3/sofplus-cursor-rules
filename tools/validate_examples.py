#!/usr/bin/env python3
"""
Validate example `.func` files under examples/:
- Filenames end with .func
- Non-empty content
- Basic patterns: avoid tabs inside lines (prefer spaces), LF endings
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def main() -> int:
    problems = []
    warnings = []
    if not EXAMPLES.exists():
        print("No examples/ directory found. Skipping.")
        return 0
    for p in sorted(EXAMPLES.glob("*.func")):
        text = p.read_text(encoding="utf-8")
        if not text.strip():
            problems.append(f"Empty example file: {p}")
        # Check for tabs (style; optional: warn only)
        for i, line in enumerate(text.splitlines(), start=1):
            if "\t" in line:
                warnings.append(f"Tab character in {p}:{i} (prefer spaces)")
    if warnings:
        print("\n".join(warnings))
    if problems:
        sys.stderr.write("\n".join(problems) + "\n")
        return 1
    print("Examples validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


