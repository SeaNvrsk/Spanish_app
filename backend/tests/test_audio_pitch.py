"""MP3 pitch shift helper."""

from app.audio_pitch import pitch_shift_mp3


def test_pitch_shift_returns_bytes():
    # Minimal valid-ish input: ffmpeg will fail on empty; skip if no ffmpeg
    import shutil

    if not shutil.which("ffmpeg"):
        return
    # Use a tiny generated tone via ffmpeg itself
    import subprocess

    proc = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.2",
            "-f",
            "mp3",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    )
    out = pitch_shift_mp3(proc.stdout, 3.0)
    assert out is not None
    assert len(out) > 100
