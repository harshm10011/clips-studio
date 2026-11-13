"""Local Ollama discovery and unified-memory-aware model recommendations."""

from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from core.macos.memory import estimate_memory_pressure, memory_snapshot, profile_for_memory


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


def release_model_for_memory_profile(
    model: str,
    host: str,
    total_bytes: int | None,
    available_bytes: int | None = None,
) -> bool:
    """Unload a local model after a finished video when headroom is tight.

    Keep Ollama warm between queued videos while memory headroom is healthy,
    avoiding a large model reload for each item. On smaller Macs, unload after
    a run when the available-memory estimate is tight or critical. When that
    estimate is unavailable, retain the conservative legacy unload behavior.
    Non-loopback hosts are never unloaded.
    """
    hostname = (urlparse(host).hostname or "").lower()
    if hostname not in {"localhost", "127.0.0.1", "::1"}:
        return False
    if not total_bytes or total_bytes > 24_000_000_000:
        return False
    if available_bytes is not None and estimate_memory_pressure(total_bytes, available_bytes) == "normal":
        return False
    return unload_ollama_model(model, host)


def model_recommendation(memory: dict | None = None) -> dict:
    snapshot = memory or memory_snapshot().as_dict()
    profile = profile_for_memory(
        int(snapshot["total_bytes"]) if snapshot.get("total_bytes") else None,
        int(snapshot["available_bytes"]) if snapshot.get("available_bytes") else None,
    )
    return profile.as_dict()
