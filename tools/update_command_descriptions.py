#!/usr/bin/env python3
"""Update YAML frontmatter `description:` in command and cvar rule files.

For each `.mdc` file under `.cursor/rules/sofplus-api/commands` and
`.cursor/rules/sofplus-api/cvars`, replace the `description:` value
with the first meaningful sentence from the document body (skips
headings, code fences and synopsis labels). The updated description
will be prefixed with the command/cvar name, e.g. "sp_sc_timer: Does X".
"""
import os
import re


def extract_description_from_body(body_text):
    # Split into lines and find the first non-empty, non-heading, non-code line
    lines = [ln.strip() for ln in body_text.splitlines()]
    in_code = False
    for ln in lines:
        if not ln:
            continue
        if ln.startswith('```'):
            in_code = not in_code
            continue
        if in_code:
            continue
        if ln.startswith('###'):
            continue
        low = ln.lower()
        if low.startswith('synopsis') or low.startswith('example') or low.startswith('parameters'):
            continue
        # skip lines that look like command invocations or single-token lines like ".players" or "sp_sc_timer"
        if ' ' not in ln and re.match(r'^[A-Za-z0-9_.\-`]+$', ln):
            continue
        # treat the first substantive line as the description
        return ln.strip(' `')
    return None


def update_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    if not text.startswith('---'):
        return False

    # Split frontmatter and body
    parts = text.split('---', 2)
    if len(parts) < 3:
        return False
    # parts: ['', '\nkey: val\n...', '\nBODY']
    front = parts[1]
    body = parts[2]

    m = re.search(r'^\s*description:\s*(.*)$', front, flags=re.MULTILINE)
    current_desc = m.group(1).strip() if m else None

    name = os.path.splitext(os.path.basename(path))[0]
    extracted = extract_description_from_body(body)
    if extracted:
        # put a space between the name and the colon: "name : description"
        new_desc = f"{name} : {extracted}"
    else:
        new_desc = name

    if current_desc == new_desc:
        return False

    # Replace (only the first occurrence) the description line while preserving indentation
    if m:
        start, end = m.span(1)
        # rebuild front by replacing the matched group
        new_front = front[:m.start(1)] + new_desc + front[m.end(1):]
    else:
        # add description as the first line in frontmatter
        new_front = 'description: ' + new_desc + '\n' + front

    new_text = '---' + new_front + '---' + body
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_text)
    return True


def main():
    root = os.path.join(os.path.dirname(__file__), '..', '.cursor', 'rules', 'sofplus-api')
    root = os.path.normpath(root)
    subdirs = ['commands', 'cvars']
    updated = []
    for sub in subdirs:
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if not fn.endswith('.mdc'):
                continue
            p = os.path.join(base, fn)
            try:
                if update_file(p):
                    updated.append(os.path.join(sub, fn))
            except Exception as e:
                print('ERROR', fn, e)

    for u in updated:
        print('Updated', u)

    print('Total updated:', len(updated))


if __name__ == '__main__':
    main()


