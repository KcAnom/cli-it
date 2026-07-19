# Timecode precision

Video/audio harnesses must be exact about time or every agent edit drifts.

## Rules

- **Internal unit**: store positions/durations as exact rational values —
  frame numbers plus a rational fps (`30000/1001`), or nanoseconds. Never
  float seconds in project state.
- **CLI input**: accept `HH:MM:SS.mmm`, plain seconds, and `Nf` (frames);
  parse to the internal unit immediately.
- **CLI output**: print both a human timecode and the exact internal value in
  `--json` output (`{"frames": 143, "fps": "30000/1001", "tc": "00:00:04;23"}`).
- **NTSC**: respect drop-frame semantics when fps is 29.97/59.94; label
  drop-frame timecodes with `;` separators.
- **Rounding**: round only at render boundaries, half-even, once. Comparisons
  in tests use the internal unit, not formatted strings.
- Delegate final placement math to the real engine where possible — the
  harness should hand the app exact values, not pre-rounded ones.
