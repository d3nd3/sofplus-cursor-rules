#!/usr/bin/env python3
"""Fix `.mdc` rule files by replacing the `name : description` delimiter
in the `description:` front-matter with `name - description`.

This script edits files under `.cursor/rules/sofplus-api/` in-place and
prints each filename it modifies.
"""
from pathlib import Path
import re
import sys

ROOT = Path(".cursor/rules/sofplus-api")
PATTERN = re.compile(r"^(description:\s*)(.*)$", re.MULTILINE)


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")

    def repl(m: re.Match) -> str:
        prefix = m.group(1)
        value = m.group(2)
        # Replace occurrences of "name : " with "name - ", but keep
        # colons that are not followed by a space (e.g. time strings hh:mm:ss).
        value = re.sub(r":\s", " - ", value)
        return prefix + value

    new = PATTERN.sub(repl, text, count=1)
    if new != text:
        path.write_text(new, encoding="utf-8")
        print(f"fixed: {path}")
        return True
    return False


def main():
    if not ROOT.exists():
        print(f"root not found: {ROOT}", file=sys.stderr)
        sys.exit(2)

    changed = 0
    for p in ROOT.rglob("*.mdc"):
        try:
            if fix_file(p):
                changed += 1
        except Exception as e:
            print(f"error: {p}: {e}", file=sys.stderr)

    print(f"total changed: {changed}")


if __name__ == "__main__":
    main()


