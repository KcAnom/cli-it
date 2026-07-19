# Sound design

- Loudness target: -14 LUFS integrated for web (`ffmpeg -af loudnorm=I=-14:TP=-1.5:LRA=11`).
- Duck music under narration by 8–12 dB (sidechaincompress, or keyframed
  volume if the NLE harness supports it).
- Fade every music edit (≥250 ms); never hard-cut ambience.
- Check the final mix in mono once — phase-cancelled music is a classic
  render surprise.
