# NLE harnesses (Shotcut / Kdenlive pattern)

Timeline-grade editing (multi-track, transitions, keyframed effects) is a
harness job, not an ffmpeg one. Upstream CLI-Anything ships Shotcut/Kdenlive
harnesses; this core recreation does not port them.

The pattern, if you build one via `cli-it-plugin/HARNESS.md`: both NLEs use
**MLT XML** as their native project format — the harness writes/edits MLT
in-process (data layer), and invokes `melt` (the real MLT engine) or the app's
headless render for output. Timecode rules: `guides/timecode-precision.md`.
