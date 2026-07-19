---
name: cli-it-matrix-video-creation
description: Capability matrix for video creation — transcode, inspect, and narrate video with real encoders. Simplified from the upstream mega-pack.
version: 0.1.0
---

# Video Creation matrix

```bash
cli-it matrix preflight video-creation --json
cli-it matrix install video-creation --dry-run
```

## Capabilities

- `video.transcode` — trim/concat/transcode (ffmpeg)
- `video.inspect` — probe streams/durations as JSON (ffprobe)
- `audio.tts` — narration audio (ElevenLabs API, or macOS `say` offline)

## Workflow stages

1. **Triage sources** — `ffprobe -v quiet -print_format json -show_streams`
   every input first; never assume codecs or durations. See
   `references/source-triage.md`.
2. **Story & audio** — script the narration, then generate audio
   (`audio.tts`). Structure guidance: `references/story-structure-audio.md`,
   `references/sound-design.md`.
3. **Assemble** — cut and concat with `video.transcode`; keep every ffmpeg
   command in a build script so the edit is reproducible.
4. **Captions** — `references/captions.md`.
5. **Render & verify** — final encode, then re-`ffprobe` the output and
   compare expected duration/streams. If a render misbehaves, run
   `scripts/video_doctor.py <file>` and see `references/render-doctor.md`.
6. **Review** — `references/art-direction-review.md` before calling it done.

## Recipes

- `narrated-clip` — `audio.tts` narration muxed over a transcoded clip:
  `ffmpeg -i clip.mp4 -i narration.wav -map 0:v -map 1:a -c:v copy out.mp4`

## Agent guidance

- Exit code 3 from preflight = gaps; continue with ready providers.
- NLE-grade timeline editing needs a harness (Shotcut/Kdenlive upstream);
  see `references/nle-shotcut-kdenlive.md` for the pattern and build one via
  `cli-it-plugin/HARNESS.md`.
- Always verify outputs with `ffprobe`, not by trusting encoder exit codes
  alone.

<!-- MATRIX_SKILL_PATHS:START -->
(rendered locally by `cli-it matrix skill video-creation`)
<!-- MATRIX_SKILL_PATHS:END -->
