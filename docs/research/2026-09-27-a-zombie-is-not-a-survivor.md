# A zombie is not a survivor

Date: 2026-09-27. Scope: the orchestrator scripts in `tests/test_integration_injection.py`
that check whether the Unix installer left any process of its test tree alive, and
`install.sh`'s `test_tree_alive`.

## What failed

The clean full run on ea2d846e, on a machine loaded by parallel runs, failed
`test_unix_installer_initial_monitor_mode_cleans_stopped_test_tree`: the survivors file
held `child.pid:828365` where it should be empty. Seven idle reruns passed.

The orchestrator decides "survived" with `kill -0 "$pid"` right after the installer has
exited. The installer killed that child; once the installer is gone the dead child is
re-parented and reaped by init or a subreaper, asynchronously. Until then it is a zombie,
and `kill -0` on a zombie succeeds. Measured here: a Python parent that does not reap a
SIGKILLed `sleep` — `kill -0` reports it alive and `ps -o stat=` prints `ZN`. Under load
the reaping lags long enough for the check to run in between. That this was the failing
run's cause is inferred from the mechanism and the idle reruns, not observed directly.

## Sources

- POSIX.1-2024, 3.426 Zombie Process: "A process whose lifetime has ended, but whose
  parent process has not yet collected its status."
  https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap03.html
- POSIX.1-2024, kill(): "If sig is 0 (the null signal), error checking is performed but
  no signal is actually sent. The null signal can be used to check the validity of pid."
  — validity of the pid, which a zombie still holds, not liveness.
  https://pubs.opengroup.org/onlinepubs/9799919799/functions/kill.html
- procps ps(1), PROCESS STATE CODES: "Z defunct ("zombie") process, terminated but not
  reaped by its parent". https://man7.org/linux/man-pages/man1/ps.1.html
- FreeBSD ps(1) (the BSD ps macOS ships): "Z Marks a dead process (a "zombie")."
  https://man.freebsd.org/cgi/man.cgi?query=ps&sektion=1

## Decision

One shell helper, `alive PID`, true only when `kill -0` succeeds and `ps -o stat= -p PID`
names no `Z` state; it is prepended to every orchestrator in the module and replaces
every `kill -0` liveness check there. Neither ps's state flags on Linux nor on BSD/macOS
use the letter Z for anything but a zombie, so matching `*Z*` is exact on both.

`install.sh` is left as it is, by analysis: `test_tree_alive` feeds `stop_test_group`'s
loop of at most five 0.1 s polls and a final `KILL` to the group. A zombie-only group costs
at most those 0.5 s and a KILL that a zombie ignores; the installer then `wait`s its own
child, so no false failure or warning follows. Changing the product for a bounded half
second would add a `ps` scan to every cleanup for no user-visible gain.

Alternatives rejected: sleeping or retrying before the check (a clock standing in for a
condition, law 6); reaping in the orchestrator (the dead child is not its child after the
installer exits); dropping the survivor assertion (weakens the test).

## Guard

`tests/test_a_zombie_is_not_a_survivor.py` runs `alive` against a real zombie (a parent
that waits with `WNOWAIT` so the child is dead and unreaped — a condition, not a sleep),
a live process and a vanished pid, and refuses any `kill -0` left in the module outside
the helper.
