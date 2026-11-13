"""Versioned, source-aware cache for deterministic audio and visual features."""

from __future__ import annotations

import json
import os
import threading
import zipfile
from pathlib import Path
from typing import Callable

import numpy as np

CACHE_VERSION = 1


def _metadata(video_path: Path, video_id: str) -> dict:
    stat = video_path.stat()
    return {
        "version": CACHE_VERSION,
        "video_id": video_id,
        "source": str(video_path.resolve()),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _load(path: Path, metadata: dict) -> tuple[dict, dict] | None:
    try:
        with np.load(path, allow_pickle=False) as archive:
            stored = json.loads(str(archive["__metadata__"].item()))
            if stored != metadata:
                return None
            audio = {
                key.removeprefix("audio__"): archive[key].copy()
                for key in archive.files if key.startswith("audio__")
            }
            visual = {
                key.removeprefix("visual__"): archive[key].copy()
                for key in archive.files if key.startswith("visual__")
            }
            return audio, visual
    except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
        return None


def _save(path: Path, metadata: dict, audio: dict, visual: dict) -> None:
    values = {"__metadata__": np.asarray(json.dumps(metadata, sort_keys=True))}
    values.update({f"audio__{key}": np.asarray(value) for key, value in audio.items()})
    values.update({f"visual__{key}": np.asarray(value) for key, value in visual.items()})
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with temporary.open("wb") as stream:
            np.savez_compressed(stream, **values)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_or_extract(
    video_path: Path,
    video_id: str,
    cache_dir: Path,
    extract_audio: Callable[[Path], dict],
    extract_visual: Callable[[Path], dict],
) -> tuple[dict, dict]:
    """Read valid cached signals or compute and atomically save them.

    The source path, size and nanosecond modification time are part of the
    key, so replacing a local import cannot silently reuse stale analysis.
    Cache failures are non-fatal: deterministic analysis still runs.
    """
    path = cache_dir / f"{video_id}.signals.npz"
    metadata = _metadata(video_path, video_id)
    if path.is_file():
        cached = _load(path, metadata)
        if cached is not None:
            print(f"      Using cached audio/visual analysis: {path.name}")
            return cached

    audio = extract_audio(video_path)
    visual = extract_visual(video_path)
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        _save(path, metadata, audio, visual)
    except OSError as exc:
        print(f"      (analysis cache not saved: {exc})")
    return audio, visual
