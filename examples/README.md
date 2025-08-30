### Examples

Place your SoFplus `.func` scripts in this directory.

- Cursor will automatically apply the `.func` quick reference for files matching `examples/*.func`.
- Keep examples focused and small; prefer one feature per file.
- Use consistent naming, e.g., `jail.func`, `voting.func`, `motd.func`.

Quick tips:
- Use dynamic cvars for per-slot state: `_prefix_$slot`
- Unescape before printing: `sp_sc_cvar_unescape ~msg ~msg`
- Schedule loops with `sp_sc_timer <ms> "cmd..."`

