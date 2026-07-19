# Source triage

Before any edit, probe every input:

```bash
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4
```

Record per source: container, video codec/profile, resolution, fps (exact
rational), audio codec/sample rate/channels, duration. Never mix
variable-frame-rate phone footage into a timeline without normalizing first
(`ffmpeg -i in.mp4 -vsync cfr -r 30 …`). Transcode odd codecs to a mezzanine
(ProRes/DNxHR or high-bitrate H.264) once, up front — not per edit.
