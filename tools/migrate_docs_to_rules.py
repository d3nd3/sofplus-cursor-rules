#!/usr/bin/env python3
"""Migrate docs/sofplus-api into .cursor/rules/sofplus-api as .mdc files.

Usage:
  python3 tools/migrate_docs_to_rules.py --copy  # copy files (default)
  python3 tools/migrate_docs_to_rules.py --move  # move files (delete originals)

This script preserves file contents and prepends a YAML frontmatter block:
---
description: <first non-title short line or empty>
alwaysApply: false
---

Backups: When copying, originals remain. When moving, originals are deleted.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
# Primary rules location
RULES = ROOT / ".cursor/rules/sofplus-api"
# Legacy docs location (optional)
DOCS = ROOT / "docs/sofplus-api"


def read_summary(p: Path) -> str:
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except Exception:
        return ""
    title_idx = None
    for i, ln in enumerate(lines[:5]):
        if ln.startswith("### "):
            title_idx = i
            break
    if title_idx is None:
        return ""
    for ln in lines[title_idx + 1 : title_idx + 4]:
        s = ln.strip()
        if s:
            return s.replace("`", "").strip()[:200]
    return ""


def migrate_dir(src_dir: Path, dst_dir: Path, move: bool) -> int:
    dst_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for p in sorted(src_dir.glob("*.md")):
        rel = p.name
        dst = dst_dir / (p.stem + ".mdc")
        summary = read_summary(p)
        front = f"---\ndescription: {summary}\nalwaysApply: false\n---\n\n"
        content = p.read_text(encoding="utf-8")
        dst.write_text(front + content, encoding="utf-8")
        count += 1
        if move:
            p.unlink()
    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--copy", action="store_true", help="Copy files (default)")
    group.add_argument("--move", action="store_true", help="Move files (delete originals)")
    args = parser.parse_args()
    move = bool(args.move)

    if not DOCS.exists():
        print(f"Source docs not found: {DOCS}")
        return 1

    cmds = DOCS / "commands"
    cvars = DOCS / "cvars"

    total = 0
    if cmds.exists():
        total += migrate_dir(cmds, RULES / "commands", move)
    if cvars.exists():
        total += migrate_dir(cvars, RULES / "cvars", move)

    print(f"Migrated {total} files to {RULES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


