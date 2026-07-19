# Story structure & audio-first editing

Write the narration script first; the audio track is the timeline's skeleton.

1. Script → TTS/VO (`audio.tts`), one file per paragraph so re-records are
   cheap.
2. Measure each narration segment (`ffprobe`) and derive the shot list from
   those durations — picture conforms to sound, not the reverse.
3. Structure: hook (≤5 s) → context → 2–4 beats → payoff/CTA. Cut anything
   that doesn't serve a beat.
4. Leave 300–500 ms of breathing room between narration segments.
