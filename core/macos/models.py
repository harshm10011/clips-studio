"""Local Ollama discovery and unified-memory-aware model recommendations."""

from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from core.macos.memory import memory_snapshot, profile_for_memory


def find_ollama_binary() -> str | None:
    binary = shutil.which("ollama")
    if binary:
        return binary
    candidates = (
        Path("/Applications/Ollama.app/Contents/Resources/ollama"),
        Path.home() / ".ollama" / "ollama",
    )
    return next((str(path) for path in candidates if path.is_file()), None)


def ollama_status(host: str = "http://127.0.0.1:11434", timeout: float = 1.5) -> dict:
    """Inspect only the local Ollama API; this function makes no internet call."""
    binary = find_ollama_binary()
    result = {
        "binary_found": bool(binary),
        "binary": binary,
        "host": host,
        "running": False,
        "models": [],
        "loaded_models": [],
        "error": "",
    }
    request = urllib.request.Request(f"{host.rstrip('/')}/api/tags", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        result["running"] = True
        result["models"] = [
            {"name": item.get("name", ""), "size_bytes": int(item.get("size", 0) or 0)}
            for item in payload.get("models", [])
            if isinstance(item, dict)
        ]
        try:
            ps_request = urllib.request.Request(
                f"{host.rstrip('/')}/api/ps", headers={"Accept": "application/json"}
            )
            with urllib.request.urlopen(ps_request, timeout=timeout) as response:
                loaded = json.loads(response.read().decode("utf-8"))
            result["loaded_models"] = [
                {"name": item.get("name", ""), "size_bytes": int(item.get("size", 0) or 0)}
                for item in loaded.get("models", [])
                if isinstance(item, dict)
            ]
        except (OSError, urllib.error.URLError, ValueError, TypeError):
            # Older Ollama versions may not expose /api/ps; inventory remains
            # useful and the optional in-memory list is simply unavailable.
            pass
    except (OSError, urllib.error.URLError, ValueError, TypeError) as exc:
        result["error"] = type(exc).__name__
    return result


def unload_ollama_model(model: str, host: str = "http://127.0.0.1:11434", timeout: float = 5.0) -> bool:
    """Ask local Ollama to release one model after a completed heavy stage."""
    request = urllib.request.Request(
        f"{host.rstrip('/')}/api/generate",
        data=json.dumps({"model": model, "keep_alive": 0}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        from core.macos.memory import ai_inference_slot

        with ai_inference_slot("Ollama model release"):
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response.read()
        return True
    except (OSError, urllib.error.URLError, ValueError):
        return False


def release_model_for_memory_profile(model: str, host: str, total_bytes: int | None) -> bool:
    """Unload a local model after a finished video on unified-memory systems.

    A 16 GB Mac processes the transcript before asking Ollama for clip analysis.
    Releasing Ollama after that video prevents its resident model from competing
    with transcription on the next queued video. Larger-memory machines keep
    the model warm for throughput. Non-loopback hosts are never unloaded.
    """
    hostname = (urlparse(host).hostname or "").lower()
    if hostname not in {"localhost", "127.0.0.1", "::1"}:
        return False
    if not total_bytes or total_bytes > 24_000_000_000:
        return False
    return unload_ollama_model(model, host)


def model_recommendation(memory: dict | None = None) -> dict:
    snapshot = memory or memory_snapshot().as_dict()
    profile = profile_for_memory(
        int(snapshot["total_bytes"]) if snapshot.get("total_bytes") else None,
        int(snapshot["available_bytes"]) if snapshot.get("available_bytes") else None,
    )
    return profile.as_dict()
