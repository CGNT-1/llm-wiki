# The installers say which branch and which warning

Date: 2026-09-26 (audit of 2026-09-27, item C-12).

## What was true

1. Both installers ended with "Code updates: nightly fast-forward of the
   checked-out branch" for any attached head. `scripts/self_update.py` follows
   only the default branch (`_update_target` -> `not_on_default_branch`), so a
   checkout left on another branch was promised updates it never gets.
2. On a scratch copy of the repository (2026-09-26), `sync_memory.py --apply`
   ended `doctor: skipped - Final doctor check requires attention.` and exit 1,
   so the installer printed "Runtime synchronization completed with warnings"
   and "LLM-Wiki installed with warnings" with no reason. Doctor at that moment
   named five checks: scheduler (never ran), capture (V3 not yet adopted), backup
   (no snapshot yet), models (weights not yet fetched), pyright (optional, not
   installed). Three of them are settled by installer steps that run after the
   sync.
3. `LLM_WIKI_INSTALL_SMOKE_TIMEOUT_SECONDS` set the installer's kill bound
   (default 180 s) while the smoke itself was always started with
   `--deadline-seconds 120`, so a larger bound could not give a slow machine a
   longer smoke.

## Sources

1. git-remote, `set-head` (https://git-scm.com/docs/git-remote, read
   2026-09-26): "Set or delete the default branch (i.e. the target of the
   symbolic-ref `refs/remotes/<name>/HEAD`) for the named remote." -- the ref
   `self_update._default_branch` reads.
2. Command Line Interface Guidelines (https://clig.dev/, read 2026-09-26):
   "If you're expecting an error to happen, catch it and rewrite the error
   message to be useful."; "Suggest commands the user should run."
3. GNU coreutils, `timeout` (read 2026-09-26): "`timeout` runs the given command
   and kills it if it is still running after the specified time interval"; with
   `--kill-after`, "The specified duration starts from the point in time when
   `timeout` sends the initial signal" -- the program's own stop comes first and
   the forced one after it, the relation the smoke's deadline and the
   installer's kill bound must keep.

## Alternatives and decisions

- Branch note. Copying the default-branch rule into bash and PowerShell would
  make three implementations of one rule. Chosen: `self_update.py --note ROOT`
  prints the note from `_update_target` itself, and both installers print it
  (`unknown - ...` if it cannot run). Every skip reason has its own sentence.
- Warnings. Suppressing the checks that later steps settle would hide a real
  failure of those steps. Chosen: the sync's doctor line names every check that
  is not ok with doctor's own message, and the installers' "with warnings"
  banner points at that line and at `scripts/doctor.py` for the state now.
  Reordering the installer so the sync's doctor runs after adoption and model
  weights is a structural change left to the owner.
- Smoke bound. A fixed margin (bound - 60 s) is negative below 60 s. Chosen: the
  smoke's deadline is two thirds of the bound, rounded up -- exactly 120 s for
  the default 180 s, 400 s for 600 s. For a bound of 1 or 2 s the two are equal;
  the kill still stops the smoke.

## Guard

`tests/test_the_installers_say_which_branch_and_which_warning.py`: the note on
the default branch, on another branch and detached, and install.sh printing the
same; the doctor line naming its checks; both banners pointing at doctor; the
smoke deadline following the bound; neither installer keeping the old promise
or a fixed 120.
