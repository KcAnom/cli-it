# Captions

- Generate SRT/VTT from the narration script (you already have exact text);
  align timestamps to the measured audio segments.
- Burn in with:
  `ffmpeg -i in.mp4 -vf "subtitles=captions.srt:force_style='FontSize=22'" out.mp4`
  or mux soft subs: `-i captions.srt -c copy -c:s mov_text`.
- Max ~2 lines / 42 chars per cue; minimum cue duration 1 s.
- Verify: extract with `ffmpeg -i out.mp4 -map 0:s:0 check.srt` and diff.
