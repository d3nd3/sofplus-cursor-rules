#!/usr/bin/env python3
"""
SoFplus docs formatter

Purpose
  Normalize Markdown formatting for files under:
    - docs/sofplus-api/commands
    - docs/sofplus-api/cvars

What it does (rendering-focused)
  - Keep first `###` heading as title. Remove an immediate duplicate plain-name line if identical to the title.
  - Normalize "Synopsis:" blocks to triple-fenced code blocks while preserving original line breaks.
  - Convert parameter name/description pairs into a compact bullet list under a "Parameters:" section.
  - Normalize "Values:" sections into a bullet list of value — meaning (or value: meaning), preserving defaults.
  - Collapse excessive blank lines (max 1) and trim trailing whitespace. Leave code blocks untouched.

What it does NOT do
  - Does not change semantics or reword descriptions
  - Does not modify content inside code fences

CLI
  Dry-run (default):
    python tools/format_sofplus_docs.py
  Show diffs for changed files:
    python tools/format_sofplus_docs.py --diff
  Write changes in-place:
    python tools/format_sofplus_docs.py --write
  Limit to commands or cvars:
    python tools/format_sofplus_docs.py --only commands
    python tools/format_sofplus_docs.py --only cvars

Exit codes
  0: success
  1: error
  2: no changes (when used with --check in the future)
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


RE_TITLE = re.compile(r"^###\s+(.+?)\s*$")
RE_CODE_FENCE_TRIPLE = re.compile(r"^```")
RE_INLINE_CODE_START = re.compile(r"^`(.*)$")  # captures content after opening backtick
RE_INLINE_CODE_END = re.compile(r"^(.*)`\s*$")  # captures content before closing backtick


@dataclass
class SectionPositions:
    synopsis_label: Optional[int]
    synopsis_start: Optional[int]
    synopsis_end: Optional[int]
    example_label: Optional[int]
    values_label: Optional[int]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def is_upper_token(line: str) -> bool:
    token = line.strip()
    if not token:
        return False
    # Allow characters commonly seen in parameter names
    # Consider uppercase tokens or tokens with spaces that are mostly uppercase
    # e.g., "DST CVAR", "SRC CVAR...", "MIN VALUE"
    letters = re.sub(r"[^A-Za-z]", "", token)
    return bool(letters) and letters.upper() == letters


def collapse_blank_lines(lines: List[str]) -> List[str]:
    new_lines: List[str] = []
    blank_streak = 0
    for ln in lines:
        if ln.strip() == "":
            blank_streak += 1
            if blank_streak <= 1:
                new_lines.append("")
        else:
            blank_streak = 0
            new_lines.append(ln.rstrip())
    # Trim leading/trailing blank lines
    while new_lines and new_lines[0] == "":
        new_lines.pop(0)
    while new_lines and new_lines[-1] == "":
        new_lines.pop()
    return new_lines


def find_sections(lines: List[str]) -> SectionPositions:
    synopsis_label = None
    synopsis_start = None
    synopsis_end = None
    example_label = None
    values_label = None

    i = 0
    while i < len(lines):
        if synopsis_label is None and lines[i].strip().lower() == "synopsis:":
            synopsis_label = i
            # Find code block start
            j = i + 1
            # skip blank lines
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines):
                if RE_CODE_FENCE_TRIPLE.match(lines[j]):
                    synopsis_start = j
                    # find matching triple fence end
                    k = j + 1
                    while k < len(lines):
                        if RE_CODE_FENCE_TRIPLE.match(lines[k]):
                            synopsis_end = k
                            break
                        k += 1
                else:
                    # Inline backtick block starting on the same line or next line
                    if RE_INLINE_CODE_START.match(lines[j]):
                        synopsis_start = j
                        # Find inline backtick closing line
                        k = j
                        while k < len(lines):
                            if RE_INLINE_CODE_END.match(lines[k]):
                                synopsis_end = k
                                break
                            k += 1
            i = j
        if example_label is None and lines[i].strip().lower() == "example:":
            example_label = i
        if values_label is None and lines[i].strip().lower() == "values:":
            values_label = i
        i += 1

    return SectionPositions(
        synopsis_label=synopsis_label,
        synopsis_start=synopsis_start,
        synopsis_end=synopsis_end,
        example_label=example_label,
        values_label=values_label,
    )


def normalize_title(lines: List[str]) -> List[str]:
    if not lines:
        return lines
    new_lines = list(lines)
    # Remove immediate duplicate plain-name line if equal to title text
    if RE_TITLE.match(new_lines[0]) and len(new_lines) >= 2:
        title_text = RE_TITLE.match(new_lines[0]).group(1)  # type: ignore[arg-type]
        second = new_lines[1].strip()
        if second == title_text:
            # Remove duplicate and a following single blank line if present
            del new_lines[1]
            if len(new_lines) > 1 and new_lines[1].strip() == "":
                del new_lines[1]
    return new_lines


def convert_inline_code_block_to_triple(lines: List[str], start: int, end: int) -> List[str]:
    # The inline block looks like: `line1 ...` (start) ... ` (end)
    # We will gather the content, strip the surrounding single backticks, and emit a fenced block.
    before = lines[:start]
    block = lines[start : end + 1]
    after = lines[end + 1 :]

    # Extract content removing a single starting and ending backtick
    content_lines: List[str] = []
    if block:
        first = block[0]
        m = RE_INLINE_CODE_START.match(first)
        content_first = m.group(1) if m else first
        content_lines.append(content_first)
        for mid in block[1:-1]:
            content_lines.append(mid)
        last = block[-1]
        m2 = RE_INLINE_CODE_END.match(last)
        if m2:
            content_lines[-1] = content_lines[-1] if len(content_lines) > 0 else ""
            # Replace last line content with captured content if present
            # When block has more than one line, the last content should be appended as a new line
            content_last = m2.group(1)
            if content_lines and content_lines[-1] != content_last:
                content_lines.append(content_last)
            elif not content_lines:
                content_lines.append(content_last)
        # Strip possible leading/trailing empty lines introduced by markup
        while content_lines and content_lines[0].strip() == "":
            content_lines.pop(0)
        while content_lines and content_lines[-1].strip() == "":
            content_lines.pop()

    fenced = ["```txt"] + content_lines + ["```"]
    return before + fenced + after


def normalize_synopsis(lines: List[str], pos: SectionPositions) -> List[str]:
    if pos.synopsis_start is None or pos.synopsis_end is None or pos.synopsis_label is None:
        return lines
    new_lines = list(lines)
    # Ensure exactly one blank line between label and code block
    # Move start to the first non-blank line after label
    # Convert inline backtick blocks to triple fences
    if new_lines[pos.synopsis_start].startswith("`") and not new_lines[pos.synopsis_start].startswith("```"):
        new_lines = convert_inline_code_block_to_triple(new_lines, pos.synopsis_start, pos.synopsis_end)
        # Recompute positions due to line count changes
        pos = find_sections(new_lines)
        if pos.synopsis_start is None or pos.synopsis_end is None:
            return new_lines
    # Ensure a blank line after label
    if pos.synopsis_label is not None:
        # Remove extra blank lines between label and block
        i = pos.synopsis_label + 1
        while i < len(new_lines) and new_lines[i].strip() == "":
            i += 1
        # Insert exactly one blank line after label
        new_lines = (
            new_lines[: pos.synopsis_label + 1]
            + [""]
            + new_lines[i:]
        )
    return new_lines


def extract_region(lines: List[str], start_after: Optional[int], stop_before: Optional[int]) -> Tuple[int, int]:
    """Return slice indices (inclusive start, exclusive end) for a region between two markers.
    If markers are None, clamp to start/end of file.
    """
    start = (start_after + 1) if start_after is not None else 0
    end = stop_before if stop_before is not None else len(lines)
    if start < 0:
        start = 0
    if end < start:
        end = start
    return start, end


def parse_name_description_pairs(lines: List[str]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if is_upper_token(line):
            name = line
            i += 1
            desc_parts: List[str] = []
            while i < len(lines):
                nxt = lines[i].strip()
                # Stop at next uppercase token or section label
                if nxt == "" or is_upper_token(nxt) or nxt.lower() in {"synopsis:", "example:", "values:", "parameters:"}:
                    break
                desc_parts.append(nxt)
                i += 1
            description = " ".join(x for x in desc_parts if x)
            if description:
                pairs.append((name, description))
            else:
                # If missing description, record placeholder to avoid data loss
                pairs.append((name, ""))
            continue
        i += 1
    return pairs


def render_pairs_as_bullets(pairs: List[Tuple[str, str]]) -> List[str]:
    if not pairs:
        return []
    out: List[str] = []
    for name, desc in pairs:
        if desc:
            out.append(f"- {name}: {desc}")
        else:
            out.append(f"- {name}:")
    return out


def normalize_parameters(lines: List[str], pos: SectionPositions) -> List[str]:
    # Parameter region is between end of Synopsis block and either Values or Example
    if pos.synopsis_end is None:
        return lines
    stop_before = None
    if pos.values_label is not None:
        stop_before = pos.values_label
    if pos.example_label is not None and (stop_before is None or pos.example_label < stop_before):
        stop_before = pos.example_label
    start, end = extract_region(lines, pos.synopsis_end, stop_before)
    region = lines[start:end]
    # Skip if the region already looks like a bullet list or starts with an explicit Parameters label
    region_text = "\n".join(region).strip()
    if not region_text or region_text.lower().startswith("parameters:") or any(l.strip().startswith("-") for l in region):
        return lines
    pairs = parse_name_description_pairs(region)
    if len(pairs) < 1:
        return lines
    bullets = ["Parameters:", ""] + render_pairs_as_bullets(pairs) + [""]
    new_lines = lines[:start] + bullets + lines[end:]
    return new_lines


def normalize_values(lines: List[str], pos: SectionPositions) -> List[str]:
    if pos.values_label is None:
        return lines
    # Values region goes until Example or end-of-file
    start, end = extract_region(lines, pos.values_label, pos.example_label)
    header_and_rest = lines[start:end]
    if not header_and_rest:
        return lines
    header = header_and_rest[0]
    rest = header_and_rest[1:]
    # Avoid double-normalizing if bullets already exist
    if any(l.strip().startswith("-") for l in rest if l.strip()):
        return lines
    # Values sections often use numeric tokens (e.g., 0/1) or free-text like "Any number".
    # Use a loose parser: take a non-empty line as a name, and the next non-empty line as its description.
    pairs: List[Tuple[str, str]] = []
    i = 0
    while i < len(rest):
        name = rest[i].strip()
        if not name:
            i += 1
            continue
        # Stop at another section label defensively
        if name.lower() in {"synopsis:", "example:", "parameters:", "values:"}:
            break
        # Find description
        j = i + 1
        desc = ""
        while j < len(rest):
            nxt = rest[j].strip()
            if nxt == "":
                j += 1
                continue
            if nxt.lower() in {"synopsis:", "example:", "parameters:", "values:"}:
                break
            # Treat only the first next non-empty line as description; do not consume further
            desc = nxt
            j += 1
            break
        pairs.append((name, desc))
        i = j if j > i else i + 1
    if not pairs:
        return lines
    bullets = [header, ""] + render_pairs_as_bullets(pairs) + [""]
    new_lines = lines[:start] + bullets + lines[end:]
    return new_lines


def normalize_examples(lines: List[str], pos: SectionPositions) -> List[str]:
    if pos.example_label is None:
        return lines
    new_lines = list(lines)
    # Ensure code block for example is fenced
    i = pos.example_label + 1
    # Skip blank lines
    while i < len(new_lines) and new_lines[i].strip() == "":
        i += 1
    if i >= len(new_lines):
        return new_lines
    # If example uses single-inline backticks across lines, convert
    if new_lines[i].startswith("`") and not new_lines[i].startswith("```"):
        # Find end line with closing backtick
        j = i
        end = None
        while j < len(new_lines):
            if new_lines[j].rstrip().endswith("`"):
                end = j
                break
            j += 1
        if end is not None:
            # Convert
            before = new_lines[:i]
            block = new_lines[i : end + 1]
            after = new_lines[end + 1 :]
            # Strip single-backticks
            content: List[str] = []
            first = block[0]
            m = RE_INLINE_CODE_START.match(first)
            content_first = m.group(1) if m else first
            content.append(content_first)
            for mid in block[1:-1]:
                content.append(mid)
            last = block[-1]
            m2 = RE_INLINE_CODE_END.match(last)
            if m2:
                last_content = m2.group(1)
                if content and content[-1] != last_content:
                    content.append(last_content)
                elif not content:
                    content.append(last_content)
            while content and content[0].strip() == "":
                content.pop(0)
            while content and content[-1].strip() == "":
                content.pop()
            fenced = ["```txt"] + content + ["```"]
            new_lines = before + fenced + after
    return new_lines


def normalize_markdown(content: str, path: Path) -> str:
    # Split keeping line breaks implicit; we will join with \n
    # Use \n regardless of original endings; repository appears to be \n-based
    lines = content.splitlines()

    # Step 1: Trim trailing whitespace and collapse blank lines early to simplify parsing
    lines = collapse_blank_lines(lines)
    # Step 2: Title de-duplication
    lines = normalize_title(lines)
    # Step 3: Find sections
    pos = find_sections(lines)
    # Step 4: Normalize synopsis block
    lines = normalize_synopsis(lines, pos)
    # Positions may have changed
    pos = find_sections(lines)
    # Step 5: Normalize parameters list
    lines = normalize_parameters(lines, pos)
    # Positions may have changed again
    pos = find_sections(lines)
    # Step 6: Normalize values list
    lines = normalize_values(lines, pos)
    # Step 7: Normalize example code block if inline
    pos = find_sections(lines)
    lines = normalize_examples(lines, pos)
    # Final cleanup: collapse blank lines again
    lines = collapse_blank_lines(lines)
    return "\n".join(lines) + "\n"


def generate_diff(a: str, b: str, path: Path) -> str:
    a_lines = a.splitlines(keepends=True)
    b_lines = b.splitlines(keepends=True)
    diff = difflib.unified_diff(a_lines, b_lines, fromfile=str(path), tofile=str(path), lineterm="")
    return "".join(diff)


def iter_markdown_files(root: Path, only: Optional[str]) -> Iterable[Path]:
    targets = []
    if only in (None, "commands"):
        targets.append(root / ".cursor/rules/sofplus-api/commands")
    if only in (None, "cvars"):
        targets.append(root / ".cursor/rules/sofplus-api/cvars")
    for base in targets:
        if not base.exists():
            continue
        for p in sorted(base.rglob("*.mdc")):
            yield p


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize SoFplus Markdown docs (commands & cvars)")
    parser.add_argument("--write", action="store_true", help="Write changes in-place (default: dry-run)")
    parser.add_argument("--diff", action="store_true", help="Show unified diff for changes")
    parser.add_argument("--only", choices=["commands", "cvars"], help="Restrict to a single category")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    changed = 0
    total = 0
    errors = 0

    for path in iter_markdown_files(root, args.only):
        total += 1
        try:
            original = read_text(path)
            normalized = normalize_markdown(original, path)
            if original != normalized:
                changed += 1
                if args.diff and not args.write:
                    sys.stdout.write(generate_diff(original, normalized, path))
                if args.write:
                    write_text(path, normalized)
                    # Also optionally show a short notice
                    sys.stdout.write(f"Updated: {path}\n")
        except Exception as exc:  # noqa: BLE001
            errors += 1
            sys.stderr.write(f"Error processing {path}: {exc}\n")

    if not args.write and not args.diff:
        sys.stdout.write(f"Scanned {total} files; {changed} would change. Use --diff to preview, --write to apply.\n")
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


