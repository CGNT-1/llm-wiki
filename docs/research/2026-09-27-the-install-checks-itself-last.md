# The install checks itself last

Date: 2026-09-27. Audit 2026-09-27, the installer-order question an earlier fix
left to the owner, decided under the owner's delegation.

## What was wrong (facts)

Both installers ran, in this order: Reliability V3 adoption (step 8), the bounded
runtime sync (8a), the pinned model weights (8b), the summary. The sync ends with
the final doctor check, and its exit code alone decides whether the installer
prints "installed with warnings".

- Reproduced offline on a tree exported from `audit27`, with a fresh state root and
  home, running adoption and `sync_memory.py --apply` exactly as the installer does.
  The final check named four findings: `models` (the pinned encoder weights are
  missing), `scheduler` (the nightly has never run), `backup` (no knowledge
  snapshot yet) and `pyright` (the optional server is not installed).
- Only `models` is settled by an installer step, and that step ran after the check.
- The same order had a second effect. The encoder loads weights local-only
  (`search_memory._get_embedder`, `onnx_encoder.load_encoder`), and the sync builds
  the first generation. Read from the code, not observed in a run: on a fresh
  install with the encoder runtime, the first generation was built with
  `vector_state: absent`, and the weights arrived one step later. Vectors waited
  for the nightly.
- CI (`timing::installer::end-to-end-linux`, run 36260843078, 2026-09-26) shows the
  symptom: "doctor: skipped - Final doctor check requires attention", then
  "Model weights step done", then "LLM-Wiki installed with warnings".

## Sources (independent, primary)

1. Argo CD, sync phases and waves
   (https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/): the PostSync
   hook "Executes after all `Sync` hooks completed and were successful, a successful
   application, and all resources in a `Healthy` state." And: "you can run smoke
   tests as PostSync hooks. If they succeed you know that your application has
   passed the validation."
2. Helm, chart tests (https://helm.sh/docs/topics/chart_tests/): tests "validate
   that your chart works as expected when it is installed", and "if you test
   immediately after this install, it is likely to show a transitive failure, and
   you will want to re-test."
3. Debian Policy, maintainer scripts
   (https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html): when
   `postinst configure` runs, "The files contained in the package will be unpacked.
   All package dependencies will at least be 'Unpacked'. If there are no circular
   dependencies involved, all package dependencies will be configured." A step runs
   after the steps it depends on.
4. Ansible, handlers
   (https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_handlers.html):
   "By default, handlers run after all the tasks in a particular play have been
   completed."

All four say the same thing in different systems: a verification belongs after
every step that changes what it verifies. A step that consumes another step's
output runs after it.

## Alternatives considered

- **Fetch the weights before the sync (chosen).** One reorder in each installer.
  The final check then runs after every step that changes what it checks. The
  first generation is built with the weights present. No extra doctor run.
- **Run a second doctor after the weights.** It fixes the verdict but not the
  vectors, and it runs the full doctor twice on every install.
- **Leave the order, but treat the `models` finding as expected during install.**
  Rejected. This hides a real finding (law 6). An install whose weights failed to
  arrive would then also end clean.

## Trade-offs

- The weights step no longer reports after the sync line. Both lines stay in the
  output, in their new order.
- A weights download that runs slowly now delays the sync, not the summary. The
  total install time is unchanged.

## What stays open (facts, not changed here)

After the reorder, a fresh install still ends "with warnings", because of three
findings no installer step settles:

- `scheduler` is `skipped` until the first nightly runs.
- `backup` is `degraded` until the first snapshot is taken.
- `pyright` is `degraded` while the optional, explicitly installed server is absent.

Whether doctor should grade the states a fresh install is expected to be in
differently is a separate question about doctor, not about the order of the
installer's steps. Suppressing those findings in the installer would be masking,
and was not done.

## Guard

`tests/test_the_install_checks_itself_last.py` reads the order in which each
installer runs its scripts. It requires that `sync_memory` runs last and that
`install_models` runs before it, for both `install.sh` and `install.ps1`. On the
old order both assertions fail for both installers.
