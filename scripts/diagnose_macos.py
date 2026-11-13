#!/usr/bin/env python3
"""Print a read-only Apple Silicon and local AI capability report as JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.macos.acceleration import detect_acceleration  # noqa: E402
from core.macos.hardware import detect_hardware  # noqa: E402
from core.macos.memory import memory_snapshot  # noqa: E402
from core.macos.models import model_recommendation, ollama_status  # noqa: E402


def build_report() -> dict:
    hardware = detect_hardware()
    memory = memory_snapshot()
    return {
        "hardware": hardware.as_dict(),
        "memory": memory.as_dict(),
        "acceleration": detect_acceleration(),
        "ollama": ollama_status(),
        "model_profile": model_recommendation(memory.as_dict()),
        "notes": [
            "Recommendations do not change the selected model or application settings.",
            "The current faster-whisper/CTranslate2 backend uses CPU on Apple Silicon; MPS is used only by compatible PyTorch models.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2, ensure_ascii=False))
