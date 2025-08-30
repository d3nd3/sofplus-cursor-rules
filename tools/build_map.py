#!/usr/bin/env python3
"""
Build a comprehensive map.json for fast lookups.

Outputs a JSON object mapping canonical names to relative doc paths, e.g.:
{
  "sp_sc_alias": "commands/sp_sc_alias.md",
  "_sp_sv_info_client_ip": "cvars/_sp_sv_info_client_ip.md",
  "dot_yes": "commands/dot_yes.md",
  "_sp_sv_sound_*": "cvars/_sp_sv_sound_asterisk.md"
}

Rules:
- Prefer explicit files; fall back to wildcard family files where applicable
- Derive names from filenames (without .md) and from index lines
- Merge duplicates, favoring explicit non-wildcard pages

CLI:
- Dry-run (stdout): python3 tools/build_map.py
- Write to docs/sofplus-api/map.json: python3 tools/build_map.py --write
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, Tuple


ROOT = Path(__file__).resolve().parents[1]
# Primary docs location is the migrated rules path
RULES_DOCS = ROOT / ".cursor/rules/sofplus-api"
# Backwards-compatible legacy docs location (optional)
DOCS = ROOT / "docs/sofplus-api"
COMMANDS_DIR = RULES_DOCS / "commands"
CVARS_DIR = RULES_DOCS / "cvars"
INDEX = RULES_DOCS / "commands_index.md"
OUTPUT = RULES_DOCS / "map.json"

# New: when building the map, also include a short one-line summary for each
# entry so agents can decide whether to open the detail page without parsing
# the page. The map value becomes either a string (legacy) or an object:
# "name": "commands/x.md"  -> legacy
# "name": { "path": "commands/x.md", "summary": "one-line summary" }


def iter_files() -> Iterable[Tuple[str, Path]]:
    # If migration target exists, prefer `.cursor/rules/sofplus-api` and read
    # `.mdc` files. Otherwise fall back to the original `docs/sofplus-api`.
    if RULES_DOCS.exists():
        cmds = RULES_DOCS / "commands"
        cvs = RULES_DOCS / "cvars"
        if cmds.exists():
            for p in sorted(cmds.glob("*.mdc")):
                yield ("commands", p)
        if cvs.exists():
            for p in sorted(cvs.glob("*.mdc")):
                yield ("cvars", p)
    else:
        if COMMANDS_DIR.exists():
            for p in sorted(COMMANDS_DIR.glob("*.md")):
                yield ("commands", p)
        if CVARS_DIR.exists():
            for p in sorted(CVARS_DIR.glob("*.md")):
                yield ("cvars", p)


def name_from_filename(p: Path) -> str:
    name = p.stem
    return name


def parse_index() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not INDEX.exists():
        return mapping
    content = INDEX.read_text(encoding="utf-8").splitlines()
    # Lines look like: - `sp_sc_alias` — command — sp_sc_alias — `commands/sp_sc_alias.md`
    line_re = re.compile(r"^-\s+`([^`]+)`\s+—\s+(?:command|cvar)\s+—\s+[^`]+\s+—\s+`([^`]+)`")
    for line in content:
        m = line_re.match(line.strip())
        if m:
            name, rel = m.groups()
            mapping[name] = rel
    return mapping


def read_summary_from_page(path: Path) -> str:
    """Return the optional one-line description (first non-title short line).

    The detail page schema allows an optional one-line description under the
    title. We strip and return that line or an empty string.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return ""
    # Skip the title line (first line that starts with "### ") and return the
    # next non-empty short line (<= 120 chars) as the summary.
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
            # sanitize backticks and excessive whitespace
            return s.replace("`", "").strip()[:200]
    return ""


def build_map() -> Dict[str, object]:
    index_map = parse_index()
    result: Dict[str, object] = {}

    # 1) Seed from filesystem
    for kind, path in iter_files():
        rel = f"{kind}/{path.name}"
        name = name_from_filename(path)
        # Wildcard family naming: *_asterisk.md maps to *_*
        if name.endswith("_asterisk"):
            star_name = name.replace("_asterisk", "_*")
            summary = read_summary_from_page(path)
            result.setdefault(star_name, {"path": rel, "summary": summary})
        else:
            summary = read_summary_from_page(path)
            result[name] = {"path": rel, "summary": summary}

    # 2) Merge from index to capture any items present only there
    for name, rel in index_map.items():
        # Prefer explicit pages over wildcard family. If the filesystem already
        # provided an entry, keep it; otherwise pull from the index. When
        # pulling from the index we attempt to read the page summary too.
        current = result.get(name)
        if current is None:
            page_path = DOCS / rel
            summary = read_summary_from_page(page_path) if page_path.exists() else ""
            result[name] = {"path": rel, "summary": summary}
        else:
            # If current is a wildcard family and index provides an explicit
            # page, replace with the explicit page from index.
            cur_path = current.get("path") if isinstance(current, dict) else None
            if cur_path and cur_path.endswith("_asterisk.md") and not name.endswith("*"):
                page_path = DOCS / rel
                summary = read_summary_from_page(page_path) if page_path.exists() else ""
                result[name] = {"path": rel, "summary": summary}

    # 3) Add dot command aliases: .yes → dot_yes
    # If an item starts with dot_, add its dot alias
    for name, rel in list(result.items()):
        if name.startswith("dot_"):
            alias = "." + name[len("dot_"):]
            # Only add if not shadowed by a real page
            result.setdefault(alias, rel)

    # Sort by key for stable output
    return dict(sorted(result.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build docs/sofplus-api/map.json")
    parser.add_argument("--write", action="store_true", help="Write to map.json (default: print to stdout)")
    args = parser.parse_args()

    mapping = build_map()
    text = json.dumps(mapping, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        OUTPUT.write_text(text, encoding="utf-8")
        print(f"Wrote {OUTPUT} ({len(mapping)} entries)")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


