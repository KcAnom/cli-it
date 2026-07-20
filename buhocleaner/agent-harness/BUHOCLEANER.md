# BUHOCLEANER.md — CLI-It Harness Analysis & Architecture

Target: `/Applications/BuhoCleaner.app` (BuhoCleaner 1.16.2, build 256,
bundle id `com.drbuho.BuhoCleaner`, © Dr.Buho Inc.). Closed-source compiled
Swift/AppKit application — analysis is of the installed bundle, not source.

## Phase 1 — Installation analysis

### Backend engine

BuhoCleaner is a GUI-only app. Its actual cleaning work (deleting caches,
logs, app leftovers) is performed by a **privileged helper tool**
(`com.drbuho.BuhoCleaner.PrivilegedHelperTool`, declared under
`SMPrivilegedExecutables` in Info.plist, shipped in
`Contents/Library/LaunchServices/`, installed to
`/Library/PrivilegedHelperTools/`). The helper is reached over XPC and its
launchd job is protected by a code-signing requirement anchored to Dr.Buho's
Developer ID (`subject.OU = S7F733N4B5`) — **it cannot and must not be driven
by third-party code**. There is:

- no command-line entry point (`Contents/MacOS/BuhoCleaner` is the GUI binary,
  169 KB stub linking `DesktopApplication.framework`),
- no AppleScript dictionary (no `.sdef` anywhere in the bundle),
- no URL scheme (`CFBundleURLTypes` absent),
- no HTTP/MCP API.

The invocable surface that *does* exist:

| Surface | Mechanism |
|---------|-----------|
| Launch / activate | `open -b com.drbuho.BuhoCleaner` |
| Uninstaller hand-off | `NSServices` entry `uninstallApplication` accepts `com.apple.application-bundle`; `open -b com.drbuho.BuhoCleaner <App.app>` hands a bundle to the app |
| Preference domain | `defaults read/write com.drbuho.BuhoCleaner` — rich, live domain (scan category toggles `*Selected`, `minimumFileSize`, window geometry, Sparkle keys) |
| Update feed | Sparkle appcast at `SUFeedURL` (`https://www.drbuho.com/buho-public-files/buhocleaner/appcast.xml`), installed version from `CFBundleShortVersionString` |
| Helper presence | `/Library/PrivilegedHelperTools/com.drbuho.BuhoCleaner.PrivilegedHelperTool` |
| Menu-bar agent | Login item `Contents/Library/LoginItems/BuhoCleanerMenu.app` |
| Quit | Apple Events `quit` (may prompt for Automation permission) |

### GUI → API map

| GUI action | Programmatic equivalent |
|------------|-------------------------|
| Toggle a Flash Clean category checkbox | `defaults write com.drbuho.BuhoCleaner <key>Selected -bool ...` (`userCacheFilesSelected`, `systemCacheFilesSelected`, `systemLogFilesSelected`, `trashCanSelected`, `screenshotFilesSelected`, `unusedDMGFilesSelected`, `mailDownloadsFilesSelected`, `browserCacheSelected`, `purgeableSpaceSelected`) |
| Large-file scan threshold | `minimumFileSize` defaults key (app's own unit; observed value `10` — passed through, never reinterpreted) |
| Run a scan / clean | **GUI only** (privileged helper, sign-gated) → harness launches the app |
| App uninstaller | `open -b com.drbuho.BuhoCleaner /Applications/Foo.app` |
| Check for updates | fetch appcast, compare `sparkle:shortVersionString` vs installed |

### Data model

- App state lives in the `com.drbuho.BuhoCleaner` defaults domain — safely
  readable always; toggles safely writable out-of-process (plain user
  preferences, re-read by the app on next launch).
- No document/project format of its own. The harness therefore owns a
  **cleanup-plan** JSON project format (`buhocleaner-plan/v1`).
- The privileged helper and its XPC protocol are **out of bounds**.

### Existing CLIs

None shipped. Nothing to wrap besides `open`, `defaults`, `pgrep`,
`osascript quit`, and the appcast URL — all isolated in
`utils/buhocleaner_backend.py`.

### Undo system

The app has none (cleaning is irreversible by nature). The harness keeps its
own session journal: plan mutations store before/after and invert cleanly;
`prefs set`/`prefs sync` journal the previous defaults values so undo can
restore them via the backend.

### Safety stance (load-bearing)

The harness **never deletes files**. Scans are read-only size probes
(`os.scandir`, permission-errors skipped). Destructive cleaning is always
delegated to the real BuhoCleaner GUI where the human confirms — `clean open`
launches it, nothing more. This is the honest mapping of principle 1 onto an
app whose engine is deliberately sealed.

## Phase 2 — CLI architecture

Entry point `cli-it-buhocleaner`; package `cli_it.buhocleaner`; REPL when no
subcommand; root `--json` flag.

### Command groups

| Group | Command | Args | Notes |
|-------|---------|------|-------|
| root | `backend` | — | probe: app path, version, running, helper, menu agent |
| `app` | `info` | — | bundle + helper + running state |
| | `launch` | — | `open -b` |
| | `quit` | — | Apple Events quit (may prompt) |
| | `update-check` | — | appcast fetch; graceful offline failure |
| `plan` | `new` | `-n NAME -o FILE` | create plan JSON + session |
| | `info` | `-p FILE` | plan summary |
| | `save` | `-p FILE` | canonical re-save |
| `category` | `list` | `-p` | categories, enabled, roots, last sizes |
| | `enable` | `-p NAME` | journaled |
| | `disable` | `-p NAME` | journaled |
| | `threshold` | `-p --mb N` | large-file threshold, journaled |
| | `root` | `-p NAME PATH` | override scan root (testing/scoping), journaled |
| `scan` | `run` | `-p [--category N]` | read-only size probe, snapshot into plan, journaled |
| | `report` | `-p` | last snapshot |
| `prefs` | `show` | — | live defaults domain |
| | `set` | `KEY VALUE --type bool\|int\|string` | journaled with previous value |
| | `sync` | `-p` | push plan category toggles → app defaults, journaled |
| `clean` | `open` | `-p [--sync]` | optional prefs sync, then launch the real app |
| `uninstall` | `open` | `APP_PATH` | hand bundle to Buho's uninstaller |
| `session` | `status` / `undo` / `redo` | `-p` | journal control |
| `preview` | `recipes` / `capture -p` / `latest` | | scan-report bundle (text+json artifacts) |

### State model

- **Plan file** (`*.json`, `buhocleaner-plan/v1`): name, per-category
  `{enabled, root}` overrides, `threshold_mb`, `last_scan` snapshot.
- **Session file** (`<plan>.session.json`): undo/redo stacks, exclusive-lock
  writes per `guides/session-locking.md` (fcntl/msvcrt portable wrapper).
- Live app prefs stay in the app's defaults domain — never copied into the
  plan except as journal `before` values.

### Categories (probe roots, all read-only)

| name | defaults toggle | default root |
|------|-----------------|--------------|
| user-caches | userCacheFilesSelected | ~/Library/Caches |
| system-caches | systemCacheFilesSelected | /Library/Caches |
| system-logs | systemLogFilesSelected | ~/Library/Logs |
| trash | trashCanSelected | ~/.Trash |
| screenshots | screenshotFilesSelected | ~/Desktop (Screenshot*/Screen Shot* only) |
| dmg-installers | unusedDMGFilesSelected | ~/Downloads (*.dmg only) |
| mail-downloads | mailDownloadsFilesSelected | ~/Library/Containers/com.apple.mail/Data/Library/Mail Downloads |
| large-files | minimumFileSize (threshold only) | ~/Downloads (≥ threshold_mb) |

### Dual output shapes (stable)

- `backend` / `app info`: `{"available", "app_path", "bundle_id", "version",
  "running", "helper_installed", "menu_agent"}` (+`install_hint` when absent)
- `scan run` / `report`: `{"plan", "scanned_at", "total_bytes", "categories":
  {name: {"root", "bytes", "files", "skipped"}}}`
- `prefs show`: `{"domain", "keys": {...}}`; errors: non-zero exit, message on
  stderr via ClickException.

### REPL & preview

REPL identical to demoapp (`ReplSkin`, copied verbatim; `buhocleaner>`
prompt). Preview recipe `scan-report` renders the last snapshot to
`artifacts/report.txt` + `report.json` via `preview_bundle` conventions.
