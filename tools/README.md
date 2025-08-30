# Tools

## format_sofplus_docs.py

Normalize Markdown formatting in `.cursor/rules/sofplus-api/commands/` and `.cursor/rules/sofplus-api/cvars/`.

- Keeps the first `###` heading as title and drops an immediate duplicate plain-name line
- Normalizes "Synopsis:" to fenced code blocks (preserving line breaks)
- Converts parameter name/description pairs into a compact bullet list under "Parameters:"
- Normalizes "Values:" sections into bullets of value — meaning, keeping defaults
- Collapses excessive blank lines and trims trailing whitespace

Does not change content inside code fences or reword descriptions.

### Usage

Dry-run (report changes):
```bash
python tools/format_sofplus_docs.py
```

Preview unified diffs:
```bash
python tools/format_sofplus_docs.py --diff
```

Write changes:
```bash
python tools/format_sofplus_docs.py --write
```

Restrict scope:
```bash
python tools/format_sofplus_docs.py --only commands
python tools/format_sofplus_docs.py --only cvars
```


## build_map.py

Build `.cursor/rules/sofplus-api/map.json` as a canonical lookup map `{ name: relative/path.mdc }`.

### Usage

Preview:
```bash
python3 tools/build_map.py
```

Write file:
```bash
python3 tools/build_map.py --write
```

Merges filesystem pages, index entries, wildcard families, and dot-command aliases.


## validate_docs.py

Run integrity checks on the docs set:
- Index entries refer to existing files
- Map entries refer to existing files
- All command/cvar pages are reachable from either index or map
- Basic schema presence (title and Synopsis)

### Usage
```bash
python3 tools/validate_docs.py
```


## validate_examples.py

Validate example `.func` files under `examples/` (non-empty, no tabs):

```bash
python3 tools/validate_examples.py
```

