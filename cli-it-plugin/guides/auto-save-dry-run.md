# Auto-save and dry-run

Two safety behaviors every mutating harness command should support.

## Auto-save

- Mutations persist by default: agents forget to call `save`, and a crash
  should never lose acknowledged work. Write project + session (locked)
  before reporting success.
- Offer `--no-save` for humans experimenting in the REPL.
- Auto-save composes with the undo journal: record the journal entry first,
  then persist, so undo state and file state can't diverge.

## Dry-run

- Every destructive or expensive command (`delete`, `render`, `export`,
  batch operations) takes `--dry-run`: print exactly what would happen —
  files written, backend command line, items affected — and exit 0 without
  doing it.
- Dry-run output must be the *real* plan (the same code path that builds the
  actual backend invocation), not a hand-maintained description.
- With `--json`, dry-run emits the plan as structured data so agents can
  inspect it before committing.
