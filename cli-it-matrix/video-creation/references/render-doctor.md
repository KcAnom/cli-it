# Render doctor

When a render looks wrong, diagnose before re-rendering:

1. `python scripts/video_doctor.py out.mp4 --json` — missing streams, zero
   duration, low bitrate, mono audio.
2. Duration drift → source was VFR; normalize inputs (see source-triage.md).
3. Black frames at cuts → keyframe-inaccurate trim; re-cut with re-encode
   (`-c:v libx264`) instead of `-c copy` at non-keyframe points.
4. A/V desync growing over time → sample-rate mismatch; resample audio to one
   rate before concat.
5. Washed-out colors → color-range flag mismatch; set `-color_range` /
   `-pix_fmt yuv420p` explicitly.
