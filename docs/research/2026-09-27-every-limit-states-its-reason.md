# Every limit states its reason (law 9) — research and proposal

Date: 2026-09-27. Status: **proposal, not implemented.** The settings file it proposes is a
structure and configuration contract change, which `CLAUDE.md` §0 reserves for the owner's
explicit yes. Inventory: `docs/LIMITS-2026-09-27.md`.

## What law 9 asks

Every limit needs an explicit basis (a user requirement, a confirmed technical limit, a
measured resource limit, a security requirement, an external contract, or a justified
trade-off); its basis, consequences and review conditions must be clear; a limit that depends
on operating conditions must be set explicitly and, where technically possible, be
configurable rather than hidden in the implementation.

## What is true today (measured 2026-09-27, read-only)

- 849 numeric limits in `scripts/` (module constants plus numeric fields of `*Limits`,
  `*Defaults`, `*Config`, `*Policy` classes). The name pattern is wider than the 2026-09-23
  inventory's (637), so the totals are not comparable.
- 346 have no `#` comment within four lines above them; 131 of those are named nowhere in
  `docs/` or `CHANGELOG.md`. A nearby comment does not prove a basis is stated, so 131 is a
  floor, not the true count of unexplained limits.
- None of the 849 can be changed without editing code. The only tunables today are a handful
  of environment variables (`MEMORY_LLM_TIMEOUT_S`, `MEMORY_OLLAMA_MAX_CONTEXT`, …) and the
  frozen `reliable_memory.ReliableMemoryDefaults`.

Classes (heuristic by name and use; the e rows and the first d rows were read in the code):

| Class | Meaning | Count | No comment and no doc |
|---|---|---|---|
| a | guard on untrusted or unbounded input (bytes, depth, entries) | 293 | 72 |
| b | protocol or platform contract (JSON-RPC integers, SQLite int64, Windows codes) | 20 | 7 |
| c | depends on operating conditions (timeouts, retention, batch sizes, leases) | 240 | 17 |
| d | cuts a list (`[:NAME]`) | 47 | 2 |
| e | hard vault-size ceiling that stops a pipeline | 12 | 2 |
| t | trims text for display | 63 | 5 |
| ? | not classified by name; needs a reading | 174 | 26 |

### The vault-size ceilings (class e), read in the code

Each raises `ValueError` when crossed; what the owner would see follows from the call path
(read in the code, not triggered live):

| Ceiling | Where | Crossed means | Live vault now |
|---|---|---|---|
| 2 000 pages, 32 MiB | `rebuild_memory_index.MAX_PAGE_COUNT`, `MAX_TOTAL_PAGE_BYTES` (`_require_within_limits`) | `knowledge/index.md` cannot be rebuilt; the compile rebuilds it inside its transaction, so the compile fails | 212 notes, 0.74 MB (11 %, 2 %) |
| 2 000 sources, 32 MiB | `compile_memory.MAX_SOURCE_COUNT`, `MAX_TOTAL_SOURCE_BYTES` (`_SourceBudget.add`) | every compile fails: `compile source count/bytes exceed limit`; the nightly reports compile FAILED | 31 daily logs + 212 notes ≈ 5.9 MB (12 %, 18 %) |
| 10 000 files, 64 MiB | `corpus_snapshot.MAX_CORPUS_FILES`, `MAX_CORPUS_TOTAL_BYTES` | no new search generation: `corpus file limit exceeded`; search keeps the last generation or reads Markdown | notes + projects + daily ≈ 290 files, 17.6 MB (3 %, 27 %); project journals are 11.7 MB of it |
| 10 000 pages | `search_memory.MAX_SEARCHABLE_PAGES` | the no-generation search refuses | 212 |
| 10 000 pages, 32 MiB | `claim_tree_manifest.MAX_CLAIM_TREE_PAGES`, `MAX_CLAIM_TREE_TOTAL_BYTES`; `claims.py` literal `10_000` | claim rebuild refuses | 212 notes |
| 10 000 sources | `knowledge_extractor.MAX_SOURCES` | extraction refuses | — |
| 2 000 files, 32 MiB | `impact_analysis.ImpactLimits.max_note_files`, `max_total_note_bytes` | impact advisory refuses | 212 |

The nearest is the corpus byte ceiling at 27 %, driven by project journals. No growth-rate
forecast is given: the vault's history before 2026-08-06 is archived and a rate from seven
weeks would be a guess.

### Cuts that drop data silently (class d, read in the code)

`episode_consolidation.MAX_ITEMS = 8` (lessons kept per consolidated day),
`ledger.MAX_RECORDS_PER_TURN = 8`, `provenance_join.MAX_NOTES_SCANNED = 500` (notes after the
500th alphabetically are never scanned). Each slices and says nothing; none has a stated
basis. `fact_keys.MAX_KEYS_PER_TURN`, `compile_memory.MAX_CLAIMS_PER_OPERATION`,
`backfill_sessions.MAX_TRANSCRIPTS`, `build_guardrails.MAX_RULES_PER_TYPE`,
`session_start_context.MAX_DECISIONS_READ` and `repository_worktrees.MAX_WORKTREES_PER_REPOSITORY`
cut the same way; whether each reports the cut was not checked here.

## Sources

- The Twelve-Factor App, III. Config: "An app's config is everything that is likely to vary
  between deploys (staging, production, developer environments, etc)." and "The twelve-factor
  app stores config in environment variables"; on grouping config: "This method does not scale
  cleanly". https://12factor.net/config
- uv, Configuration files: "If project-, user-, and system-level configuration files are found,
  the settings will be merged, with project-level configuration taking precedence over the
  user-level configuration, and user-level configuration taking precedence over the
  system-level configuration." and "Settings provided via environment variables take
  precedence over persistent configuration, and settings provided via the command line take
  precedence over both." https://docs.astral.sh/uv/concepts/configuration-files/
- systemd.unit(5), drop-ins: "This is useful to alter or add configuration settings for a
  unit, without having to modify unit files." and "All files with the suffix ".conf" from this
  directory will be merged in the alphanumeric order and parsed after the main unit file itself
  has been parsed." https://man7.org/linux/man-pages/man5/systemd.unit.5.html
- Ruff, Configuring Ruff: "If no config file is found in the filesystem hierarchy, Ruff will
  fall back to using a default configuration." https://docs.astral.sh/ruff/configuration/

What they agree on: defaults ship in the program; a user's override lives outside the shipped
files and is layered on top; environment variables override files for one run. Twelve-factor
argues for environment variables, but it is written for deployed services; a local tool with
dozens of knobs (uv, ruff, systemd) keeps them in a file and uses the environment for the
exception.

## Alternatives

1. **One environment variable per knob.** Simple to read, no new file. Rejected as the main
   channel: ~250 tunables (classes c and e) as variables are undiscoverable, and the
   scheduler, the hooks and the MCP server each start with a different environment, so the
   same vault could run with different limits depending on who started the process.
2. **Keep constants, write the basis next to each.** Satisfies the "basis" half of law 9 and
   costs least. Does not satisfy "configurable where it depends on operating conditions" for
   classes c and e. Right for classes a, b and t.
3. **One typed settings registry plus one optional user file (recommended).**
   - `scripts/settings.py`: one frozen dataclass per area; each field carries its default,
     unit, lower and upper bound, and a one-line basis. Code reads limits only through it.
   - Override file: `llm-wiki.toml` at the vault root, gitignored, absent by default. TOML is
     already a dependency (`tomllib`/`tomli`).
   - Precedence as in uv: code default < file < `LLM_WIKI_<SECTION>_<KEY>` environment
     variable for one run.
   - Fail loud: an unknown key, a wrong type or an out-of-bounds value stops the process with
     the key's name. A limit never silently falls back to its default.
   - `doctor` gains a `settings` section. It shows every value that differs from its default
     and where it came from. For class e it compares the live size with the ceiling and warns
     at 80 %, before the stop. Every class-e refusal names the setting that raises it.

## Recommendation

Alternative 3 for classes c and e, alternative 2 for classes a, b and t, and for class d a
reported count of what was cut (`dropped: N`) in the answer or the log, plus a basis; a cut
that drops durable data (lessons, ledger records, fact keys, claims) becomes a setting.

Trade-offs: a new tracked module and a new user-owned file at the vault root. Every knob
becomes a contract that must stay backward compatible. Tests need a way to inject settings;
the registry takes an explicit mapping instead of reading global state. Only class c and e
limits become tunable, about 250; guards against hostile input stay constants, because making
them tunable invites raising them past what the code was measured to survive.

## What needs the owner's yes

1. A new file at the vault root (`llm-wiki.toml`, gitignored), and the env-variable prefix
   `LLM_WIKI_<SECTION>_<KEY>`. This is a structure and env-contract change (CLAUDE.md §0),
   recorded in `docs/STRUCTURE.md`.
2. Whether the class-e ceilings stay hard stops (raised on request) or become warnings. The
   recommendation is to keep the stops: they bound memory, since each pipeline holds its
   inputs in memory. Doctor warns early, and the refusal names the setting.

## Effort (estimate, not measured)

- Registry, loader, doctor section and tests: about 1 day.
- Moving class c and e (~250 limits) into it, module by module with their tests: 2–3 days.
- Class d reporting (~47 cuts): about 1 day.
- Basis comments for classes a, b, t and hand-classifying the 174 "?": 1–2 days.

Total 5–7 working days.

## Decision (2026-09-27)

The owner delegated the choice to the nine laws ("делай в соответствии с правилами");
alternative 3 is taken. Phase 1, built:

- `scripts/settings.py` holds the registry (`Setting`: section, key, default, unit,
  reason, lower bound) and the only reader, `setting_value(name, root)`. The file is
  read with the bounded reader (64 KiB) on every call and parsed once per distinct
  content (keyed by its SHA-256; keyed by size and modification time it returned a stale
  value when the file was rewritten at the same length within one filesystem clock tick,
  caught by a test under load 2026-09-27); a vault without the file pays the reader's
  lookups and no parse.
- `llm-wiki.toml` at the vault root is gitignored (`/llm-wiki.toml`). Precedence is
  default < file < `LLM_WIKI_<SECTION>_<KEY>`; an unknown section or key, a bool, a
  string, a value below its bound or broken TOML raises `SettingsError` naming the
  key and its source.
- No upper bound is registered: the ceilings bound the memory a pipeline holds, and
  an operator who raises one owns that memory. A bound invented here would be the
  unjustified limit law 9 forbids.
- The twelve class-e ceilings moved into it with their old values (index, compile,
  corpus, claims, extraction, search, impact); `doctor.DEFAULT_GENERATION_SOURCE_LIMIT`,
  a second copy of the corpus file ceiling, went with them. Every refusal names the
  setting that lifts it.
- `doctor` has a `settings` check: overrides with their source, `error` on an invalid
  file, `degraded` at 80 % of a ceiling, counted from the Markdown under
  `knowledge/notes`, `projects` and `daily` that each pipeline reads.

Phase 2a (class c), built. The rule applied to each class-c limit: it becomes a setting
only if an operator would reasonably change it for their machine and it is tied to no
other value by a contract; otherwise it stays a constant whose basis is written above it,
and "basis unknown — value predates measurement; review when …" where none can be stated
from the code, a note or a measurement. Law 6 decided the rest: a setting nobody should
turn is an abstraction without a user.

- Settings (6, section `retention`): `report_days`, `report_files`, `report_bytes`,
  `telemetry_days`, `benchmark_run_days`, `config_backup_days` — retention of disposable
  diagnostics, a disk-against-hindsight choice. Their constants are gone.
- Constants kept, and why: lease/heartbeat pairs and the writer gate's retry schedule
  (a ratio every live owner relies on); budgets nested in the host's 5-second hook or in a
  caller's deadline; the Reliability v3 defaults (`ReliableMemoryDefaults`, the plan of
  2026-07-13 and CLAUDE.md's 90 hot days); the LSP evidence's 14 days (a CLAUDE.md
  contract); CLI defaults an operator already sets per run (`doctor --time-budget`,
  `sync_memory --time-limit-seconds`, `MEMORY_LLM_TIMEOUT_S`).
- 45 bases written in this pass, 17 of them "basis unknown" with a review condition; 164
  earlier comments kept without re-reading; 8 rows in files another change owned are not
  worked. One constant read by nothing (`doctor.LOCK_STALE_SECONDS`) is gone, one
  duplicate of the archive contract (`archive_daily.DEFAULT_HOT_DAYS`) now reads it.
- Guard: `tests/test_every_limit_states_its_reason.py` fails on any module-level limit in
  `scripts/` with no comment within four lines above it and no setting, against the
  debt list `tests/fixtures/law9-unexplained-limits.txt` (209, classes a, b, d, t and
  unclassified). A comment is a mechanical proxy: it proves a reason was written, not
  that it is right.

Added to phase 2a on 2026-09-27:

- `provider.draft_ceiling_seconds` (600) replaces `compile_memory.COMPILE_PROVIDER_CEILING_S`
  and `episode_consolidation.CONSOLIDATION_PROVIDER_CEILING_S` (both 300, "the same
  bound"). Evidence: 24 compile drafts through the claude CLI on a copy of the vault took
  99 to 418 s each while test runs loaded the machine, so 300 s cut legitimate drafts;
  2026-08-28 measured one call over 90 s, a pass of 225 s and a day that compiled at
  600 s. 600 s is the largest observed call with about 1.4 times headroom. An unbounded
  wait is refused: a stuck provider would hold the compile lock and the nightly until the
  scheduler killed the pass. `MEMORY_LLM_TIMEOUT_S` keeps its precedence over every call.
  `llm_client.DEFAULT_TIMEOUT_S` (90 s) stays a constant: that variable is already its
  knob, and a second one for the same value would be duplicate configuration.
- Class-d sites in these modules (the rule of
  `docs/research/2026-09-27-a-cut-says-what-it-left-out.md`): a claim past
  `MAX_CLAIMS_PER_OPERATION` is reported as dropped; doctor's claims finding counts the
  pages it does not name (`pages_omitted`); `MAX_OPERATIONAL_ROWS`,
  `MAX_RUNTIME_ENTRIES` and `MAX_LSP_OWNER_ROWS` were already disclosed as truncated
  scans; `PENDING_CLAIM_WINDOW` leaves the rest queued; `_FRAME_EDGE_BYTES` only reads
  the edges of a refused frame; `GRAPH_SEED_LIMIT` is a ranking parameter;
  `MAX_DECISIONS_READ` is a sampling window whose total is printed. One silent loss was
  found and fixed: the navigation answer read every CALLS edge up to
  `MAX_NAVIGATION_GRAPH_FACTS` (10 000) and filtered for the symbol afterwards, so in a
  repository with more call edges a symbol's callers could be missing without a word;
  the read is now anchored on the symbol's nodes in SQL (`_anchored_call_edges`), in
  slices of `evidence_graph.MAX_NODE_FILTER` (512) that the reader accepts. The call-edge
  verifier had the same shape and is anchored the same way; every other `graph.edges`
  read in `scripts/` already named its nodes (impact analysis was fixed for the same
  loss in audit 3, A14). Guard: `tests/test_a_cut_in_the_core_says_what_it_left_out.py`
  (5 tests, all fail on the code before; one of them fails on any unanchored
  `graph.edges` call).

## Closed: private_vault_backup.py (2026-09-27)

The machine owner changed the law-8 leftover-copy rule: a backup extension (`.bak`,
`.orig`, `.old`, `.rej`, `~`) is still refused always, while a word suffix (`_old`,
`_backup`, `_copy`, ...) is refused only when the original it copies exists beside it
(the gate's own suite: 223 of 223). `private_vault_backup.py` copies nothing, so it can be
edited: `_validate_command` and `_validate_root_locations` are split
(`_valid_command_item`, `_require_separate_sources`), and its four limits state their
basis. Both exception lists are gone: the two-if guard and the limit guard now require
zero offenders across the code.
