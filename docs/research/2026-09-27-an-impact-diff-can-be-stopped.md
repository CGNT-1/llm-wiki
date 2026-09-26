# An impact diff can be stopped

Date: 2026-09-27. Audit 2026-09-27, finding A-5 (my regression from B-8, 0c348182).

## What was wrong (reproduced)

B-8 split one changed file into its separate edits with `difflib.SequenceMatcher`
over up to 20 000 lines between the common ends. Nothing inside that call checks the
deadline or a cancel. Measured by the auditor with a 5 s deadline: `lsp_process.py`
with every 10th line reformatted was still running when killed at 110 s; 5 000
repeated lines took 22.7 s. Re-checked here: the new test's 10 000-line case did not
finish in 300 s on the old code. All that time an MCP worker slot is held.

## Alternatives considered

1. Poll the deadline inside a hand-written diff. Rejected: a second diff
   implementation to maintain, and still in the MCP process.
2. Keep `difflib` and lower `MAX_DIFF_LINES`. Rejected: a smaller number with no basis
   (law 9), and the cost is superlinear below any cap.
3. Chosen: run Git's own diff (`git diff --no-index --unified=0`) on the two middles in
   a temporary directory, through the same `_git` child that the deadline and a cancel
   already kill (41eba99a), and read the hunk headers. `MAX_DIFF_LINES` and the
   `difflib` import are removed.

Measured after: the reformatted `lsp_process.py` 0.02 s (728 hunks); 5 000 repeated
lines 0.01 s. On identical repeated lines Git may align an edit as an insertion plus a
deletion rather than a replacement; both are minimal diffs, and real code rarely has
long runs of identical lines, where the edits map exactly (tested).

Same class, not changed: `model_dlp._changed_line_blocks` also uses `SequenceMatcher`,
on a prompt against its scrubbed copy — almost every line equal, size bounded by the
prompt. Left as is, named here.

## Sources (fetched 2026-09-27)

- Python documentation, difflib, https://docs.python.org/3/library/difflib.html —
  "difflib's algorithm is quadratic time for the worst case and has expected-case
  behavior dependent in a complicated way on how many elements the sequences have in
  common; best case time is linear."
- Git documentation, git-diff, https://git-scm.com/docs/git-diff — `--no-index`: "This
  form is to compare the given two paths on the filesystem. … This form implies
  --exit-code", which "exits with 1 if there were differences and 0 means no
  differences."
- GNU diffutils manual, Overview, https://www.gnu.org/software/diffutils/manual/html_node/Overview.html —
  "The basic algorithm is described by Eugene W. Myers in 'An O(ND) Difference
  Algorithm and its Variations', Algorithmica Vol. 1, 1986, pp. 251–266."

Conclusion (mine): an O(ND) diff in a killable child answers in milliseconds and
stops when told; a quadratic in-process match does neither.

## Files

- `scripts/impact_analysis.py`
- `tests/test_an_impact_diff_can_be_stopped.py`
