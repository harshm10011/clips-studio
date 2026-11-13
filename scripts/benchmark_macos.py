#!/usr/bin/env python3
"""Measure local FFmpeg VideoToolbox encode throughput on Apple Silicon.

The synthetic test pattern avoids touching creator footage. Results measure
the FFmpeg filter/VideoToolbox encode path, not transcription or the full AI
pipeline. See docs/MACOS_MIGRATION_PLAN.md for how to run the full profile.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.binaries import ffmpeg

RESOLUTIONS = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "4k": (3840, 2160),
}


def _csv_ints(raw: str, label: str) -> list[int]:
    try:
        values = [int(item.strip()) for item in raw.split(",") if item.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{label} must be comma-separated integers") from exc
    if not values or any(value < 1 for value in values):
        raise argparse.ArgumentTypeError(f"{label} values must be positive")
    return values


def _encoder_available(name: str) -> bool:
    result = subprocess.run(
        [ffmpeg(), "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=30
    )
    return name in f"{result.stdout}\n{result.stderr}".split()


def _peak_rss(proc: subprocess.Popen) -> int | None:
    try:
        import psutil

        process = psutil.Process(proc.pid)
        peak = 0
        while proc.poll() is None:
            try:
                peak = max(peak, process.memory_info().rss)
            except psutil.Error:
                pass
            time.sleep(0.1)
        return peak or None
    except ImportError:
        proc.wait()
        return None


def run_case(name: str, seconds: int, width: int, height: int, encoder: str) -> dict:
    command = [
        ffmpeg(), "-hide_banner", "-nostats", "-loglevel", "error",
        "-f", "lavfi", "-i", f"testsrc2=size={width}x{height}:rate=30",
        "-t", str(seconds), "-an", "-c:v", encoder, "-b:v", "8M",
        "-pix_fmt", "yuv420p", "-f", "null", "-",
    ]
    started = time.perf_counter()
    proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    peak_rss = _peak_rss(proc)
    stderr = proc.stderr.read() if proc.stderr else ""
    elapsed = time.perf_counter() - started
    if proc.returncode != 0:
        raise RuntimeError(f"{name} {seconds}s failed: {stderr[-1200:]}")
    return {
        "resolution": name,
        "width": width,
        "height": height,
        "seconds": seconds,
        "elapsed_seconds": round(elapsed, 3),
        "frames_per_second": round(seconds * 30 / max(elapsed, 0.001), 1),
        "realtime_factor": round(seconds / max(elapsed, 0.001), 2),
        "process_peak_rss_bytes": peak_rss,
        "encoder": encoder,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolutions", default="720p,1080p",
                        help="comma-separated choices: 720p,1080p,4k")
    parser.add_argument("--lengths", default="5,15",
                        help="comma-separated synthetic clip lengths in seconds")
    args = parser.parse_args(argv)

    if platform.system() != "Darwin":
        parser.error("this benchmark measures the macOS VideoToolbox encoder")
    resolutions = [item.strip().lower() for item in args.resolutions.split(",")]
    invalid = [item for item in resolutions if item not in RESOLUTIONS]
    if invalid:
        parser.error(f"unknown resolution: {', '.join(invalid)}")
    try:
        lengths = _csv_ints(args.lengths, "lengths")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    if any(length > 3600 for length in lengths):
        parser.error("benchmark lengths are limited to one hour")

    encoder = "h264_videotoolbox"
    if not _encoder_available(encoder):
        parser.error("this FFmpeg build does not include h264_videotoolbox")

    print(json.dumps({"machine": platform.machine(), "encoder": encoder,
                      "note": "Synthetic encode benchmark; not a full AI pipeline run."}))
    for name in resolutions:
        width, height = RESOLUTIONS[name]
        for seconds in lengths:
            print(json.dumps(run_case(name, seconds, width, height, encoder)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
