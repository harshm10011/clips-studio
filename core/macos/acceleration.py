"""Runtime checks for Apple and NVIDIA acceleration.

Checks are deliberately lazy and fail closed. A diagnostic must never make a
video job fail just because an optional runtime cannot be inspected.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from typing import Any


def mps_usable(torch_module: Any | None = None) -> tuple[bool, str]:
    """Whether the installed PyTorch build can use Apple's MPS device."""
    try:
        if torch_module is None:
            import torch as torch_module
    except Exception as exc:
        return False, f"PyTorch did not load ({type(exc).__name__})"

    try:
        mps = torch_module.backends.mps
        if not mps.is_built():
            return False, "PyTorch was built without MPS support"
        if not mps.is_available():
            return False, "PyTorch reports MPS unavailable (check its build and macOS support)"
        return True, "Apple Metal Performance Shaders (MPS)"
    except Exception as exc:
        return False, f"could not check MPS ({type(exc).__name__})"


def run_with_device_fallback(models: Any, device: str, operation, label: str):
    """Run a model on its selected accelerator, retrying once on CPU.

    ``models`` may be one module or a sequence such as a network and its
    classification head. The first real inference is the compatibility check;
    an unsupported kernel demotes future PyTorch work to CPU too.
    """
    try:
        return operation(device)
    except Exception as exc:
        if device == "cpu":
            raise
        objects = models if isinstance(models, (tuple, list)) else (models,)
        for model in objects:
            try:
                model.to("cpu")
            except Exception:
                pass
        from core.gpu import force_torch_cpu

        reason = f"{device.upper()} {label} failed ({str(exc)[:90]})"
        force_torch_cpu(reason)
        print(f"      {label}: accelerator unavailable ({str(exc)[:90]}) — retrying on CPU")
        return operation("cpu")


def ensure_model_device(model: Any, device: str) -> str:
    """Move a cached PyTorch or Ultralytics model only when its device changed."""
    module = getattr(model, "model", model)
    try:
        current = next(module.parameters()).device.type
    except (AttributeError, StopIteration, TypeError):
        current = None
    if current != device:
        model.to(device)
    return device


def coreml_status() -> dict:
    """Report the OS Core ML runtime separately from the optional Python tools."""
    native_available = sys.platform == "darwin"
    try:
        toolkit_available = importlib.util.find_spec("coremltools") is not None
    except (ImportError, ValueError):
        toolkit_available = False
    return {
        "native_runtime_available": native_available,
        "python_tools_installed": toolkit_available,
        "note": (
            "Core ML is provided by macOS; coremltools is needed for Python model conversion."
            if native_available else "Core ML requires macOS."
        ),
    }


def videotoolbox_status(ffmpeg: str | None = None) -> dict:
    """Check FFmpeg's encoder registry instead of assuming the codec exists."""
    executable = ffmpeg or shutil.which("ffmpeg")
    if not executable:
        return {"available": False, "encoders": [], "reason": "FFmpeg was not found"}
    try:
        result = subprocess.run(
            [executable, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        output = f"{result.stdout}\n{result.stderr}"
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": False, "encoders": [], "reason": f"FFmpeg check failed ({type(exc).__name__})"}
    encoders = [name for name in ("h264_videotoolbox", "hevc_videotoolbox") if name in output]
    return {
        "available": bool(encoders),
        "encoders": encoders,
        "reason": "" if encoders else "This FFmpeg build does not list VideoToolbox encoders",
    }


def detect_acceleration() -> dict:
    """Return a compact capability report for vision, transcription and video."""
    from core.gpu import cuda_usable

    mps, mps_reason = mps_usable()
    cuda, cuda_reason = cuda_usable()
    if mps:
        vision_device, vision_reason = "mps", mps_reason
    elif cuda:
        vision_device, vision_reason = "cuda", cuda_reason
    else:
        vision_device, vision_reason = "cpu", f"{mps_reason}; {cuda_reason}"

    from core.binaries import ffmpeg

    os_is_macos = sys.platform == "darwin"
    return {
        "pytorch": {
            "vision_device": vision_device,
            "mps_available": mps,
            "mps_reason": mps_reason,
            "cuda_available": cuda,
            "cuda_reason": cuda_reason,
        },
        "coreml": coreml_status(),
        "transcription": {
            "engine": "faster-whisper / CTranslate2",
            "device": "cuda" if cuda else "cpu",
            "note": (
                "The current CTranslate2 backend does not use MPS or Core ML; "
                "Whisper runs on CPU on this Mac until a supported local backend is added."
                if os_is_macos and not cuda else "Uses the available CTranslate2 backend."
            ),
            "whisperkit_cli": bool(shutil.which("whisperkit-cli")),
        },
        "video_toolbox": videotoolbox_status(ffmpeg()),
    }
