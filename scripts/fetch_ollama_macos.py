"""Fetch the pinned universal macOS Ollama runtime for ClipForge.

    python scripts/fetch_ollama_macos.py
    python scripts/fetch_ollama_macos.py --force

The release archive and its SHA-256 are taken from Ollama's official GitHub
release. The source is checked before extraction; the resulting `ollama`
binary must contain an Apple Silicon slice.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "vendor" / "ollama"
VERSION = "v0.40.16"
ASSET = "ollama-darwin.tgz"
URL = f"https://github.com/ollama/ollama/releases/download/{VERSION}/{ASSET}"
SHA256 = "a743717494315da7cd352982b805f6b992d4b4452ca117fd5fbf86c4ee46fca0"

NOTICE = f"""Ollama {VERSION}
================

This application bundles the unmodified universal macOS Ollama runtime.
Ollama is distributed under the MIT License. Its source and release archive:

  https://github.com/ollama/ollama
  {URL}

The archive checksum verified by the build fetcher is:
  SHA-256 {SHA256}

The MIT license text is included in the upstream release archive where
provided. The app starts Ollama as a separate process on localhost and stores
model data in the user's ClipForge Application Support folder.
"""


def verify_arm64(binary: Path) -> None:
    result = subprocess.run(["lipo", str(binary), "-verify_arch", "arm64"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{binary} has no arm64 slice: {result.stderr.strip()}")


def fetch(force: bool = False) -> int:
    if sys.platform != "darwin":
        raise RuntimeError("The macOS runtime fetcher must run on macOS.")
    existing = DEST / "ollama"
    if existing.is_file() and not force:
        verify_arm64(existing)
        print(f"Ollama {VERSION} already staged at {existing}")
        return 0

    print(f"Downloading Ollama {VERSION} from {URL}")
    request = urllib.request.Request(URL, headers={"User-Agent": "ClipForge-macOS-build"})
    with urllib.request.urlopen(request, timeout=180) as response:
        archive_bytes = response.read()
    digest = hashlib.sha256(archive_bytes).hexdigest()
    if digest != SHA256:
        raise RuntimeError(f"Ollama SHA-256 mismatch: got {digest}, expected {SHA256}.")

    DEST.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="clipforge-ollama-") as temp_name:
        temp = Path(temp_name)
        archive = temp / ASSET
        archive.write_bytes(archive_bytes)
        extract = (temp / "extracted").resolve()
        extract.mkdir()
        with tarfile.open(archive, "r:gz") as tar:
            # The pinned archive is hash-verified. Still reject absolute paths
            # and parent traversal before handing entries to tarfile.
            members = tar.getmembers()
            for member in members:
                target = (extract / member.name).resolve()
                if target != extract and extract not in target.parents:
                    raise RuntimeError(f"Unsafe path in Ollama archive: {member.name}")
            tar.extractall(extract, members=members)

        candidates = list(extract.rglob("ollama"))
        if not candidates:
            raise RuntimeError("The Ollama archive did not contain its runtime binary.")
        source_root = candidates[0].parent
        verify_arm64(candidates[0])
        staged = temp / "staged"
        shutil.copytree(source_root, staged, symlinks=True)
        (staged / "VERSION.txt").write_text(f"{VERSION}\n", encoding="utf-8")
        (staged / "README-OLLAMA.txt").write_text(NOTICE, encoding="utf-8")
        if DEST.exists():
            shutil.rmtree(DEST)
        staged.rename(DEST)

    print(f"Staged Ollama {VERSION} at {DEST}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="replace the staged runtime")
    args = parser.parse_args()
    try:
        return fetch(args.force)
    except Exception as exc:
        print(f"Ollama staging failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
