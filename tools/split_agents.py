#!/usr/bin/env python3
"""Split AGENTS.html into per-command and per-cvar markdown files.

Creates:
 - .cursor/rules/sofplus-api/commands/<id>.mdc
 - .cursor/rules/sofplus-api/cvars/<id>.mdc

This is a best-effort parser using simple HTML sectioning to keep the script
dependency-free. If `AGENTS.html` is not present the script exits with a
clear message.
"""
import os
import re
import html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'AGENTS.html')
OUT_BASE = os.path.join(ROOT, '.cursor', 'rules', 'sofplus-api')
CMDS_DIR = os.path.join(OUT_BASE, 'commands')
CVARS_DIR = os.path.join(OUT_BASE, 'cvars')

if not os.path.exists(SRC):
    print(f"Source file not found: {SRC}\nNothing to split. If you have AGENTS.html, place it at the repository root.")
    raise SystemExit(1)

os.makedirs(CMDS_DIR, exist_ok=True)
os.makedirs(CVARS_DIR, exist_ok=True)

with open(SRC, 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

# Split into top-level sections by <h2 id="..."> ... </h2>
dt_global_re = re.compile(r'<dt[^>]*\bid="(?P<id>[^"]+)"[^>]*>(?P<title_html>.*?)</dt>(?P<body>.*?)(?=(<dt[^>]*\bid=)|</dl>|<h2\s+id=|\Z)', re.S)

def html_to_md(s: str) -> str:
    s = s.replace('\r', '')
    # <br> -> newline
    s = re.sub(r'<br\s*/?>', '\n', s)
    # code -> `code`
    s = re.sub(r'<code>(.*?)</code>', lambda m: '`' + m.group(1).strip() + '`', s, flags=re.S)
    # headings inside dt (rare) -> keep as bold
    s = re.sub(r'<h3[^>]*>(.*?)</h3>', lambda m: '**' + m.group(1).strip() + '**\n', s, flags=re.S)
    # remove lists but keep text
    s = re.sub(r'</?(ul|li|dl|dt|dd|div|span)[^>]*>', '\n', s)
    # remove remaining tags
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    # normalize multiple newlines
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

found = 0
# Walk all dt entries globally
for m in dt_global_re.finditer(text):
    cid = m.group('id')
    title_html = m.group('title_html')
    body_html = m.group('body')
    md = html_to_md(title_html + '\n\n' + body_html)
    header = f"### {cid}\n\n"
    content = header + md + '\n'
    # classify as cvar if id begins with '_' or contains '_sp_' or starts with '_sp'
    if cid.startswith('_') or '_sp_' in cid or cid.startswith('_sp'):
        out_dir = CVARS_DIR
    else:
        out_dir = CMDS_DIR
    safe_name = re.sub(r'[^0-9A-Za-z._-]', '_', cid)
    # Emit .mdc files with a small YAML frontmatter so they are immediately
    # usable as agent rules. Use the first non-empty line of the body as a
    # short summary when available.
    summary = ""
    for ln in md.splitlines():
        s = ln.strip()
        if s and not s.startswith("###"):
            summary = s.replace('`', '')[:200]
            break
    front = f"---\ndescription: {cid} - {summary}\nalwaysApply: false\n---\n\n"
    out_path = os.path.join(out_dir, safe_name + '.mdc')
    with open(out_path, 'w', encoding='utf-8') as out:
        out.write(front + content)
    found += 1

print(f'Wrote {found} files into {CMDS_DIR} and {CVARS_DIR}')


