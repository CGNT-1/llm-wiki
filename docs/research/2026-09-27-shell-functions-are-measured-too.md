# Shell functions are measured too

Date: 2026-09-26 (audit of 2026-09-27, law 5).

## What was true

The machine gate that measures every edit covers 26 languages and skips `.sh`.
CI checked `install.sh` with `bash -n` and shellcheck only. Five installer
functions had grown past the ceiling of 5, counted the way the section below
defines: `stop_test_child` 14 (nesting 3), `protect_push_urls` 10,
`configure_codex_mcp` 7, `fetch_pinned_checkout` 7, `stop_test_timer` 7.

## Sources

1. lizard README, https://github.com/terryyin/lizard (read 2026-09-26). The
   supported-language list is "C# (C Sharp), C/C++ (works with C++14), Erlang,
   Fortran, GDScript, Golang, Java, JavaScript (With ES6 and JSX), Kotlin, Lua,
   Objective-C, Perl, PHP, PL/SQL, Python, R, Ruby, Rust, Scala, Solidity,
   Structured Text (St), Swift, TTCN-3, TypeScript (With TSX), VueJS, Zig" --
   no shell. lizard 1.24.0 reads an unknown extension with
   `(get_reader_for(filename) or CLikeReader)` (`lizard.py:615`), so a `.sh`
   file is measured as C: `elif`, `until` and `case` arms are not decisions to it.
   On the old `install.sh` it gave no warning for `configure_codex_mcp` while the
   function had three `case` outcomes, two `if` and one `||`.
2. NIST SP 500-235, McCabe and Watson, "Structured Testing", section 4.2,
   https://www.mccabe.com/pdf/mccabe-nist235r.pdf (read 2026-09-26): "An 'if'
   statement, 'while' statement, and so on are binary decisions, and therefore
   add one to complexity. Boolean operators add either one or nothing to
   complexity, depending on whether they have short-circuit evaluation
   semantics"; for a multiway decision "The number added is one less than the
   number of edges out of the decision node"; "An implicit default or
   fall-through branch, if specified by the language, must be taken into
   account". On limits: "The original limit of 10 as proposed by McCabe has
   significant supporting evidence" -- the owner's law sets 5, stricter.
3. shellmetrics 0.5.0, https://github.com/shellspec/shellmetrics (read
   2026-09-26): measures "NLOC - Non-comment Lines of Code, LLOC - Logical Lines
   of Code, CCN - Cyclomatic Complexity number" for "bash, mksh, yash, zsh"; its
   flags are "`-s/--shell`, `--[no-]color`, `--csv`, `-p/--pretty`,
   `-d/--debug`, `-v/--version`, and `-h/--help`" -- no threshold, no failing
   exit code. Run here it gave the old `protect_push_urls` 3, for a function
   with a loop, an `if` and seven `||`: it does not count `||` after a
   line continuation.
4. ShellCheck README, https://github.com/koalaman/shellcheck (read
   2026-09-26): its goals are syntax issues, "intermediate level semantic
   problems" and "subtle caveats, corner cases and pitfalls"; it does not
   measure complexity.

## Alternatives

- lizard with its C reader: the same tool as the machine gate, but it does not
  know the shell and under-counts `case` and `elif`, which is how
  `configure_codex_mcp` passed it at 7.
- shellmetrics: shell-aware, but no CI exit code, not on PyPI (a pinned download
  in CI and a vendored copy for local runs), and it under-counts `||`.
- A counter on tree-sitter-bash (chosen): the grammar is already a dev and
  `code-graph` dependency (`scripts/code_extractor.py:47`), so nothing new is
  installed; the grammar names `elif_clause`, `case_item`, `while_statement`
  (which carries `until` too), `for_statement`, `c_style_for_statement` and the
  `&&`/`||` tokens, so each of NIST's decisions is one node type. It also
  measures the law's nesting of `if`/`for`/`while`, which neither tool does for
  shell.

## Decision

`tests/test_shell_functions_stay_simple.py` measures every tracked `.sh` file:
each `if`, `elif`, loop, `&&` and `||` adds one; a `case` arm adds one unless it
is a lone `*)` default (NIST's implicit-default rule); nesting of
`if`/`for`/`while` stays at 2 or less. Unit cases pin each counting rule, so a
counter that stopped seeing a construct fails. The five functions were split
into steps of one purpose each; the installer's behaviour is unchanged, with one
exception: `configure_codex_mcp` no longer reports success when copying the
config to `config.bak` fails (it returned 0 before, because the function runs
inside `if` where `set -e` is off).

## Trade-offs

- The counter is ours, about forty lines; its rules are pinned by tests and by
  the NIST text above, not by a third-party tool's version.
- The top-level body of `install.sh` is not a function and is not measured;
  shellmetrics puts its decision count at 63. Splitting it is a larger change
  that the law does not require.
