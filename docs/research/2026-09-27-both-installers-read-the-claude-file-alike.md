# Both installers read the Claude file alike

Date: 2026-09-26 (audit of 2026-09-27, item C-11).

## What was true

`install.ps1` read `~/.claude.json` with `ConvertFrom-Json`. Claude Code keeps
one key per project path there, and two spellings of one path (`/srv/Repo`,
`/srv/repo`) are two keys. Reproduced in pwsh 7.6.6 on 2026-09-26:
"Cannot convert the JSON string because it contains keys with different casing.
Please use the -AsHashTable switch instead." The installer then called the file
`unreadable`, printed no registration command, and reported "MCP server not
registered". `install.sh` read the same file with Python, which accepted it, but
it too printed nothing for a file it could not read.

## Sources

1. PowerShell docs, ConvertFrom-Json (7.6, updated 2026-06-16),
   https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/convertfrom-json :
   `-AsHashtable` "was introduced in PowerShell 6.0"; Example 4:
   "The JSON string contains two key value pairs with keys that differ only in
   casing. Without the switch, the command would have thrown an error."
2. RFC 8259, section 8.3: implementations comparing names "code unit by code
   unit, are interoperable in the sense that implementations will agree in all
   cases on equality or inequality of two strings" -- `Repo` and `repo` are two
   names. Section 4: "The names within an object SHOULD be unique."
3. Python `json` (standard library): object members become `dict` keys, which
   compare exactly, so both spellings are kept; the installers already run
   Python helpers from `scripts/installer_config.py` for OpenCode and the sync
   plan.

## Alternatives

- `ConvertFrom-Json -AsHashtable`: fixes PowerShell 6+, but the installer also
  supports Windows PowerShell 5.1, which has no such switch; a second 5.1 path
  (`JavaScriptSerializer`) would be a third reader to keep in agreement.
- Keep two readers: the installers already disagreed once (this item).
- One reader for both installers (chosen): `installer_config.py
  claude-mcp-state --config <file> --vault-root <vault>`, run through
  `uv run --locked --no-sync` as the OpenCode step is. It compares the vault
  path with `os.path.normcase`, so Windows keeps the case-insensitive match
  PowerShell's `-contains` gave it and POSIX stays exact.

## Decision

Both installers ask the helper. An `unreadable` state now prints why nothing was
registered and the `claude mcp add` command to run once the file reads, in both
installers. `tests/test_both_installers_read_the_claude_file_alike.py` covers
every state in Python and runs each installer's function over a file with
case-differing keys; the PowerShell case fails on the old reader.

## Trade-offs

- Reading the file now needs the synced environment. The installers reach this
  step only after the sync, and a failed helper reads as `unreadable`, which
  prints the command rather than hiding it.
- The file is read whole, as both old readers did; no size bound is added, since
  its size is Claude Code's and not ours to cap.
