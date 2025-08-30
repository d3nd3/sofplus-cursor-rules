### sofplus-cursor-docs

Documentation for the SoFplus scripting language, optimized for use with the Cursor assistant.

### What this project contains

- `.cursor/rules/sofplus-api/` (agent-visible copies / canonical index)
  - `commands/`: one `.mdc` file per command (agent rules)
  - `cvars/`: one `.mdc` file per cvar (agent rules)
  - `map.json`: generated quick lookup map used by tools (canonical index)
-.cursor/rules/ (agent-visible rules and quickrefs)
  - `sofplus_lookup_rules.mdc`: lookup/answer formatting (agents prefer this)
  - `sofplus_func_quickref.mdc`: `.func` quick reference when editing scripts
  - `sofplus-api/`: migrated command and cvar pages as `.mdc` files with frontmatter
- `tools/`
  - `format_sofplus_docs.py`: formatter to normalize Markdown across commands/cvars
  - `README.md`: usage for tools
  - `build_map.py`: generate/update `docs/sofplus-api/map.json`
  - `validate_docs.py`: integrity checks for index, map, and pages
- `examples/`: place your `.func` example scripts here

### How it works (map‑first, agent‑friendly)

1. Prefer `.cursor/rules/sofplus-api/map.json` for O(1) lookups (it includes short summaries).
2. Agents should consult `.cursor/rules/sofplus-api/*.mdc` (auto‑loaded by Cursor) for detail pages.
3. When answering questions, quote the exact `Synopsis:` block from the detail page and include a minimal example.

### Formatting and conventions

- Each detail page uses this schema:
  - Title as `### <name>`
  - Optional one‑line description
  - `Synopsis:` followed by a fenced code block
  - Optional `Parameters:` as bullets `NAME: description`
  - Optional `Values:` as bullets `value: meaning` (include defaults if relevant)
  - Optional `Example:` as a minimal fenced block
- Wildcard families: files ending with `asterisk.md` represent `*_` families (e.g., `_sp_sv_sound_*`).
- Dot commands are stored without a leading dot in filenames (e.g., `.yes` → `dot_yes.md`).

### Tooling

- Preview formatting changes:
  - `python3 tools/format_sofplus_docs.py --diff`
- Apply formatting:
  - `python3 tools/format_sofplus_docs.py --write`
- Limit scope:
  - `--only commands` or `--only cvars`

### For the assistant

- Cursor auto-loads project rules from `.cursor/rules/`.
- Detailed command/cvar pages are now available under `.cursor/rules/sofplus-api/` as `.mdc` files with YAML frontmatter:
  - `description`: one-line summary used to decide whether to open the page
  - `alwaysApply: false` (default; assistant can include the rule when relevant)
- Prefer `map.json` for lookups; open detail pages only when needed. Do not preload large artifacts like `AGENTS.html`.

- Scoping rules to a specific project/folder

- To restrict these agent rules to a particular set of scripts, copy the `.cursor/rules/`
  directory into the folder that contains your `.func` scripts. Cursor will auto-load
  rules from the nearest `.cursor/rules/` ancestor, so placing a copy next to your
  scripts ensures the rules only apply when working in that folder.

### Quickstart

- Format docs: `make format` (or `python3 tools/format_sofplus_docs.py --write`)
-- Build map: `make map` (or `python3 tools/build_map.py --write`) — the builder writes `.cursor/rules/sofplus-api/map.json` and includes summaries.
- Validate: `make validate` (or `python3 tools/validate_docs.py`)
- Validate examples: `make validate-examples` (requires example files under `examples/`)


