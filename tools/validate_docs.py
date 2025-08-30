#!/usr/bin/env python3
"""
Validate SoFplus docs integrity:
- Index points to existing files
- Map points to existing files
- All command/cvar pages are present in either index or map
- Minimal schema check: title and Synopsis label exist
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
# Primary docs location is the migrated rules path
RULES_DOCS = ROOT / ".cursor/rules/sofplus-api"
# Backwards-compatible legacy docs location (optional)
DOCS = ROOT / "docs/sofplus-api"
COMMANDS_DIR = RULES_DOCS / "commands"
CVARS_DIR = RULES_DOCS / "cvars"
INDEX = RULES_DOCS / "commands_index.md"
MAP_JSON = RULES_DOCS / "map.json"


def read_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    # If file is a .mdc with YAML frontmatter, strip it for schema validation
    if path.suffix == ".mdc" and text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip('\n')
    return text


def parse_index_paths() -> Dict[str, str]:
    if not INDEX.exists():
        return {}
    out: Dict[str, str] = {}
    for line in read_text(INDEX).splitlines():
        # - `name` — command|cvar — alias — `commands/sp_sc_alias.md`
        if line.strip().startswith("- ") and "`" in line:
            parts = line.split("`")
            if len(parts) >= 4:
                name = parts[1]
                rel = parts[3]
                out[name] = rel
    return out


def parse_map_paths() -> Dict[str, str]:
    """Parse `map.json` and return a mapping name -> relative path.

    The new `map.json` may map to objects {"path": ..., "summary": ...} or
    legacy strings. Normalize to name->path for validation purposes.
    """
    if not MAP_JSON.exists():
        return {}
    try:
        raw = json.loads(read_text(MAP_JSON))
    except Exception:
        return {}
    out: Dict[str, str] = {}
    for name, val in raw.items():
        if isinstance(val, str):
            out[name] = val
        elif isinstance(val, dict) and "path" in val:
            out[name] = val["path"]
    return out


def iter_pages() -> List[Path]:
    pages: List[Path] = []
    # Prefer migrated `.mdc` files when present
    if RULES_DOCS.exists():
        cmds = RULES_DOCS / "commands"
        cvs = RULES_DOCS / "cvars"
        if cmds.exists():
            pages += sorted(cmds.glob("*.mdc"))
        if cvs.exists():
            pages += sorted(cvs.glob("*.mdc"))
    else:
        if COMMANDS_DIR.exists():
            pages += sorted(COMMANDS_DIR.glob("*.md"))
        if CVARS_DIR.exists():
            pages += sorted(CVARS_DIR.glob("*.md"))
    return pages


def check_file_exists(rel: str) -> bool:
    # Accept files referenced either in the original `docs/sofplus-api` or the
    # migrated `.cursor/rules/sofplus-api`. Also tolerate .md <-> .mdc extension
    # mismatches.
    candidates = [DOCS / rel, RULES_DOCS / rel]
    # If rel ends with .md, also check for .mdc in RULES_DOCS; if it ends with
    # .mdc, also check for .md in DOCS.
    if rel.endswith(".md"):
        candidates.append(RULES_DOCS / (Path(rel).parent / (Path(rel).stem + ".mdc")))
    if rel.endswith(".mdc"):
        candidates.append(DOCS / (Path(rel).parent / (Path(rel).stem + ".md")))
    return any(p.exists() for p in candidates)


def validate_schema(path: Path) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    text = read_text(path)
    lines = text.splitlines()
    title_line = next((ln for ln in lines[:3] if ln.startswith("### ")), None)
    has_title = title_line is not None
    has_synopsis = any(ln.strip().lower() == "synopsis:" for ln in lines)
    if not has_title:
        errors.append("missing title (### <name>)")
    if not has_synopsis:
        errors.append("missing Synopsis:")
    # Title/name alignment: title text should match filename stem, except wildcard families
    if title_line:
        title_text = title_line[4:].strip()
        stem = path.stem
        # allow families *_asterisk and dot-command pages (dot_ prefix)
        if stem.endswith("_asterisk"):
            expected = stem
        else:
            expected = stem
        if title_text != expected:
            errors.append(f"title/name mismatch: title='{title_text}' file='{stem}'")
    return (len(errors) == 0, errors)


def main() -> int:
    problems: List[str] = []

    index_paths = parse_index_paths()
    map_paths = parse_map_paths()

    # 1) Index references must exist
    for name, rel in index_paths.items():
        if not check_file_exists(rel):
            problems.append(f"Index points to missing file: {name} -> {rel}")

    # 2) Map references must exist
    for name, rel in map_paths.items():
        if rel and not check_file_exists(rel):
            problems.append(f"Map points to missing file: {name} -> {rel}")

    # 3) All pages should be present in index or map
    all_known = set(index_paths.values()) | set(map_paths.values())
    for p in iter_pages():
        rel = f"{p.parent.name}/{p.name}"
        if rel not in all_known:
            problems.append(f"Unreferenced page (not in index or map): {rel}")

    # 4) Minimal schema
    for p in iter_pages():
        ok, errs = validate_schema(p)
        if not ok:
            for e in errs:
                problems.append(f"Schema issue in {p}: {e}")

    if problems:
        sys.stderr.write("\n".join(problems) + "\n")
        return 1
    print("Docs validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


