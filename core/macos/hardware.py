"""Dependency-light host hardware detection for macOS and development hosts."""

from __future__ import annotations

import platform
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class HardwareInfo:
    system: str
    architecture: str
    os_version: str
    chip: str
    total_memory_bytes: int | None
    apple_silicon: bool

    @property
    def total_memory_gb(self) -> float | None:
        if self.total_memory_bytes is None:
            return None
        return round(self.total_memory_bytes / 1024**3, 1)

    def as_dict(self) -> dict:
        result = asdict(self)
        result["total_memory_gb"] = self.total_memory_gb
        return result


def _command(*args: str, timeout: float = 2.0) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def total_memory_bytes() -> int | None:
    """Return physical RAM bytes without requiring psutil or another package."""
    if sys.platform == "darwin":
        raw = _command("sysctl", "-n", "hw.memsize")
        try:
            value = int(raw)
            return value if value > 0 else None
        except (TypeError, ValueError):
            # Managed environments may deny sysctl access. system_profiler
            # exposes the public hardware summary without exposing its serial
            # number or UUID in our output.
            match = re.search(r"^\s*Memory:\s*(\d+)\s*GB\s*$", _system_profiler(), re.MULTILINE)
            return int(match.group(1)) * 1024**3 if match else None

    try:
        pages = int(os.sysconf("SC_PHYS_PAGES"))
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        return pages * page_size if pages > 0 and page_size > 0 else None
    except (OSError, ValueError, AttributeError):
        return None


def _system_profiler() -> str:
    try:
        result = subprocess.run(
            ["system_profiler", "-detailLevel", "mini", "SPHardwareDataType"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def detect_hardware() -> HardwareInfo:
    system = platform.system()
    architecture = platform.machine() or "unknown"
    is_darwin = sys.platform == "darwin"
    chip = _command("sysctl", "-n", "machdep.cpu.brand_string") if is_darwin else ""
    system_summary = _system_profiler() if is_darwin and not chip else ""
    if system_summary:
        chip_match = re.search(r"^\s*Chip:\s*(.+?)\s*$", system_summary, re.MULTILINE)
        if chip_match:
            chip = chip_match.group(1)
    if not chip:
        chip = platform.processor() or architecture
    os_version = platform.mac_ver()[0] if is_darwin else platform.release()
    memory = total_memory_bytes()
    if memory is None and system_summary:
        match = re.search(r"^\s*Memory:\s*(\d+)\s*GB\s*$", system_summary, re.MULTILINE)
        if match:
            memory = int(match.group(1)) * 1024**3
    apple_silicon = is_darwin and architecture.lower() in {"arm64", "aarch64"}
    return HardwareInfo(
        system=system,
        architecture=architecture,
        os_version=os_version or "unknown",
        chip=chip,
        total_memory_bytes=memory,
        apple_silicon=apple_silicon,
    )
