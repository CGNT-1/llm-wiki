# A sectionless configuration is the server's own

Date: 2026-09-26 (audit of 2026-09-27, item C-8).

## What was true

`pyright_session._configuration_result` answered a `workspace/configuration`
item without a `section` with `PYRIGHT_CONFIGURATION`, whatever profile the
session ran. The same session class runs Pyright, typescript-language-server,
gopls and rust-analyzer (`lsp_profiles.REGISTRY`), so a gopls asking for its
whole configuration was told Pyright's `python.analysis` settings instead of
its own `build.allowImplicitNetworkAccess: false`. A named section was already
read from the session's own profile.

## Sources

1. LSP 3.17 specification, `workspace/configuration`
   (https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/,
   source `_specifications/lsp/3.17/workspace/configuration.md`, read
   2026-09-26): `section?: string` -- "The configuration section asked for.";
   "If the client can't provide a configuration setting for a given scope then
   `null` needs to be present in the returned array."
2. vscode-languageclient, `client/src/common/configuration.ts` (main, read
   2026-09-26): for an item without a section it runs
   `workspace.getConfiguration(undefined, resource)` and returns every key of
   it -- the client's whole configuration.
3. Neovim, `runtime/lua/vim/lsp/handlers.lua` (master, read 2026-09-26):
   "-- If no section is provided, return settings as is" followed by
   `table.insert(response, client.settings)` -- the settings of the client that
   the asking server belongs to.

## Alternatives

- Answer `null` for a sectionless item: allowed by source 1, but a server that
  asks for its whole configuration would then run on its own defaults, which
  for gopls include implicit network access the profile turns off.
- Keep a per-profile special case: the session already holds the profile's
  settings, so a second lookup would duplicate them.
- Answer the session's own settings (chosen): what both reference clients do,
  and for Pyright the same bytes as before.

## Decision and guard

A sectionless item returns the settings the session's profile answers for any
section. `tests/test_a_sectionless_configuration_is_the_servers_own.py` checks
every registered profile, so a profile added later is covered; it fails on the
old code for the three non-Pyright profiles. The unused `PYRIGHT_CONFIGURATION`
and `thaw_pyright_profile_value` imports left `pyright_session.py`.
