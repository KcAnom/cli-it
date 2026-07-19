# Session locking

Harness session files are shared mutable state: an agent may run several
commands in quick succession, or a human REPL and an agent may touch the same
project. Every session **write** must therefore hold an exclusive lock.

## The pattern

Open `r+` (create first if missing), lock, read, mutate, seek/truncate, write,
release. Locking `r+` on the *same* handle avoids the classic
open-truncate-then-lock race that can leave another reader with an empty file.

```python
import fcntl, json, os
from pathlib import Path


def update_session(path: Path, mutate) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("{}", encoding="utf-8")
    with open(path, "r+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)        # blocks until exclusive
        try:
            try:
                state = json.load(fh)
            except ValueError:
                state = {}
            state = mutate(state)
            fh.seek(0)
            fh.truncate()
            json.dump(state, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    return state
```

## Rules

- **Windows**: use `msvcrt.locking` behind the same helper (see the demoapp
  harness `core/session.py` for a portable wrapper).
- Lock scope is the *file handle*, so do all IO inside the `with` block.
- Keep the critical section short — never call the software backend while
  holding the lock.
- Reads may go lockless *if* a torn read only degrades to a retry; otherwise
  take a shared lock (`LOCK_SH`).
- One session file per project file, next to it or under the project's
  `.cli-it/` directory — never a global session for all projects.
