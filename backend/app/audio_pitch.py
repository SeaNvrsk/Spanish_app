"""Lightweight MP3 pitch shift for Angélica child voice (requires ffmpeg)."""

from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def pitch_shift_mp3(data: bytes, semitones: float) -> bytes | None:
    """Raise pitch by semitones while keeping duration. Returns None if ffmpeg unavailable."""
    if not data or semitones == 0:
        return data
    if not shutil.which("ffmpeg"):
        logger.warning("ffmpeg not found — skipping pitch shift")
        return None

    factor = 2 ** (semitones / 12.0)
    atempo = 1 / factor
    proc = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-filter:a",
            f"asetrate=44100*{factor:.6f},aresample=44100,atempo={atempo:.6f}",
            "-f",
            "mp3",
            "pipe:1",
        ],
        input=data,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        logger.warning("ffmpeg pitch shift failed: %s", proc.stderr.decode(errors="replace")[:200])
        return None
    return proc.stdout
