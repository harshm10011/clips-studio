"""Optional H.264/H.265 MP4 export transcoding.

Rendered clips stay in the fast H.264 format. Export can copy that file as-is
or transcode it to a chosen codec and bitrate without changing the library copy.
"""

import subprocess
import sys
from pathlib import Path

from core.binaries import ffmpeg


def _encoders() -> set[str]:
    try:
        result = subprocess.run(
            [ffmpeg(), "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        return set()
    return set(f"{result.stdout}\n{result.stderr}".split())


def transcode_export(
    source: Path,
    target: Path,
    codec: str,
    bitrate_kbps: int | None = None,
) -> str:
    """Write a new MP4 export, returning the encoder used.

    Apple hardware encoding is preferred on macOS; libx264/libx265 provide
    software fallback when FFmpeg includes them. Failed hardware runs are
    retried with the software encoder before reporting an error.
    """
    if codec not in ("h264", "h265"):
        raise ValueError("Choose H.264 or H.265 for export.")
    if bitrate_kbps is not None and not 1000 <= bitrate_kbps <= 50000:
        raise ValueError("Export bitrate must be between 1,000 and 50,000 kb/s.")

    bitrate = bitrate_kbps or (6000 if codec == "h265" else 8000)
    names = _encoders()
    candidates = (
        ["hevc_videotoolbox", "libx265"] if codec == "h265" and sys.platform == "darwin"
        else ["libx265"] if codec == "h265"
        else ["h264_videotoolbox", "libx264"] if sys.platform == "darwin"
        else ["libx264"]
    )
    candidates = [name for name in candidates if name in names]
    if not candidates:
        label = "H.265" if codec == "h265" else "H.264"
        raise RuntimeError(f"This FFmpeg build has no available {label} export encoder.")

    partial = target.with_name(f"{target.stem}.partial{target.suffix}")
    errors: list[str] = []
    for encoder in candidates:
        args = ["-c:v", encoder, "-b:v", f"{bitrate}k"]
        if encoder in ("libx264", "libx265"):
            args += ["-preset", "faster", "-maxrate", f"{round(bitrate * 1.5)}k",
                     "-bufsize", f"{bitrate * 2}k"]
        elif encoder.endswith("_videotoolbox"):
            args += ["-maxrate", f"{round(bitrate * 1.5)}k"]
        if codec == "h265":
            args += ["-tag:v", "hvc1"]
        command = [
            ffmpeg(), "-y", "-v", "error", "-i", str(source),
            "-map", "0:v:0", "-map", "0:a?", *args,
            "-c:a", "copy", "-movflags", "+faststart", str(partial),
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True)
        except Exception as exc:
            errors.append(f"{encoder}: {exc}")
            partial.unlink(missing_ok=True)
            continue
        if result.returncode == 0 and partial.is_file():
            partial.replace(target)
            return encoder
        errors.append(f"{encoder}: {result.stderr[-500:] or 'encoder failed'}")
        partial.unlink(missing_ok=True)

    raise RuntimeError("Export encoding failed. " + " | ".join(errors))
