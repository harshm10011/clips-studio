"""Conservative memory profiles and single-slot AI inference coordination."""

from __future__ import annotations

import gc
import threading
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Iterator

_AI_INFERENCE_LOCK = threading.BoundedSemaphore(1)


@dataclass(frozen=True)
class MemorySnapshot:
    total_bytes: int | None
    available_bytes: int | None
    source: str

    def as_dict(self) -> dict:
        result = asdict(self)
        result["total_gb"] = _gb(self.total_bytes)
        result["available_gb"] = _gb(self.available_bytes)
        return result


@dataclass(frozen=True)
class MemoryProfile:
    tier: str
    max_model_memory_bytes: int | None
    max_concurrent_ai_jobs: int
    recommendation: str
    reason: str

    def as_dict(self) -> dict:
        result = asdict(self)
        result["max_model_memory_gb"] = _gb(self.max_model_memory_bytes)
        return result


def _gb(value: int | None) -> float | None:
    return round(value / 1024**3, 1) if value is not None else None


def memory_snapshot() -> MemorySnapshot:
    """Use psutil when installed, with a standard-library total-RAM fallback."""
    try:
        import psutil

        memory = psutil.virtual_memory()
        return MemorySnapshot(int(memory.total), int(memory.available), "psutil")
    except Exception:
        from core.macos.hardware import total_memory_bytes

        total = total_memory_bytes()
        available = None
        try:
            import os

            available = int(os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE"))
        except (OSError, ValueError, AttributeError):
            pass
        return MemorySnapshot(total, available, "system counters" if available else "total RAM only")


def profile_for_memory(total_bytes: int | None, available_bytes: int | None = None) -> MemoryProfile:
    """Choose a conservative local model budget for unified or system memory.

    This is a recommendation only; it never changes the user's selected Ollama
    model or edits settings.yaml. 16 GB Apple Silicon maps to the normal tier
    and the repository's tested 4B local model, leaving headroom for macOS and
    video buffers.
    """
    if not total_bytes or total_bytes < 12_000_000_000:
        tier = "low"
        recommendation = "gemma3:4b"
        reason = "Keep the local language model small and process one heavy job at a time."
        cap_fraction = 0.40
    elif total_bytes < 24_000_000_000:
        tier = "normal"
        recommendation = "gemma3:4b"
        reason = "A 4B model leaves room for macOS, transcription and video buffers on 16 GB systems."
        cap_fraction = 0.48
    else:
        tier = "high"
        recommendation = "gemma3:12b"
        reason = "More memory can support a larger local model; verify actual model size before loading."
        cap_fraction = 0.55

    available_basis = available_bytes if available_bytes and available_bytes > 0 else total_bytes
    model_cap = int(min(total_bytes * cap_fraction, available_basis * 0.70))
    return MemoryProfile(
        tier=tier,
        max_model_memory_bytes=model_cap,
        max_concurrent_ai_jobs=1,
        recommendation=recommendation,
        reason=reason,
    )


def estimate_memory_pressure(total_bytes: int | None, available_bytes: int | None) -> str:
    """Estimate memory pressure from available RAM without claiming Apple's
    private pressure score. The UI pairs this heads-up with available bytes.
    """
    if not total_bytes or total_bytes <= 0 or available_bytes is None:
        return "unknown"
    available = max(0, int(available_bytes))
    fraction = available / total_bytes
    if available < 1_500_000_000 or fraction < 0.10:
        return "critical"
    if available < 3_000_000_000 or fraction < 0.20:
        return "tight"
    return "normal"


@contextmanager
def ai_inference_slot(name: str = "local AI") -> Iterator[None]:
    """Serialize heavyweight local inference to protect unified-memory headroom."""
    _AI_INFERENCE_LOCK.acquire()
    try:
        yield
    finally:
        _AI_INFERENCE_LOCK.release()


def release_torch_cache(device: str | None = None) -> None:
    """Drop unused framework cache after an explicit model lifecycle boundary."""
    gc.collect()
    try:
        import torch

        with ai_inference_slot("framework cache release"):
            if device:
                selected = device
            else:
                from core.gpu import torch_device

                selected = torch_device()
            if selected == "mps":
                torch.mps.empty_cache()
            elif selected == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
    except Exception:
        # Cache release is best effort; it must never turn a completed job into
        # a failed one on systems with an older PyTorch build.
        return
