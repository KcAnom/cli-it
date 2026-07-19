#!/usr/bin/env python3
"""video_doctor — quick health report for a rendered video file.

Usage: python video_doctor.py <media-file> [--json]

Wraps ffprobe (real tool; must be installed) and flags common render problems:
missing streams, zero duration, absurd bitrates, mono audio where stereo was
likely intended.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def probe(path: Path) -> dict:
    if shutil.which("ffprobe") is None:
        sys.exit("ffprobe not found — install with: brew install ffmpeg")
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"ffprobe failed on {path}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def diagnose(doc: dict) -> list[str]:
    findings: list[str] = []
    streams = doc.get("streams", [])
    fmt = doc.get("format", {})
    video = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]

    if not video:
        findings.append("no video stream")
    if not audio:
        findings.append("no audio stream (intentional for silent clips)")
    duration = float(fmt.get("duration", 0) or 0)
    if duration <= 0:
        findings.append("zero/unknown duration — likely truncated render")
    bitrate = int(fmt.get("bit_rate", 0) or 0)
    if video and bitrate and bitrate < 100_000:
        findings.append(f"suspiciously low bitrate ({bitrate} b/s)")
    for stream in audio:
        if int(stream.get("channels", 2)) == 1:
            findings.append("mono audio — confirm this is intended")
    return findings


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--json"]
    as_json = "--json" in sys.argv
    if not args:
        sys.exit(__doc__)
    path = Path(args[0])
    if not path.is_file():
        sys.exit(f"file not found: {path}")
    doc = probe(path)
    findings = diagnose(doc)
    if as_json:
        print(json.dumps({"file": str(path), "findings": findings, "ok": not findings}))
    else:
        print(f"video_doctor: {path}")
        if findings:
            for finding in findings:
                print(f"  ! {finding}")
        else:
            print("  ✓ no problems detected")
    sys.exit(0 if not findings else 3)


if __name__ == "__main__":
    main()
