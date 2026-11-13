"""Build the native Apple Silicon ClipForge backend and Electron installers.

Run inside a clean Python 3.11 ARM64 virtual environment after installing
requirements-macos.txt and running `npm ci` in ui/. FFmpeg is staged from the
build host, its non-system dylibs are copied and rewritten to app-relative
paths, and the pinned Ollama runtime is fetched with checksum verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui"
VENDOR_FFMPEG = ROOT / "vendor" / "ffmpeg"
BACKEND_OUT = ROOT / "build" / "dist" / "backend"
MIN_FREE_GB = 30


def run(args: list[str], cwd: Path = ROOT, *, capture: bool = False,
        env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    if not capture:
        print("  +", " ".join(str(x) for x in args), flush=True)
    try:
        return subprocess.run(args, cwd=cwd, check=True, text=True,
                              capture_output=capture, env=env)
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            print(exc.stdout[-6000:])
        if exc.stderr:
            print(exc.stderr[-6000:], file=sys.stderr)
        raise


def require(command: str, why: str) -> str:
    value = shutil.which(command)
    if not value:
        raise RuntimeError(f"Missing {command}: {why}")
    return value


def verify_arm64(path: Path) -> None:
    result = subprocess.run(["lipo", str(path), "-verify_arch", "arm64"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{path} is not an Apple Silicon binary: {result.stderr.strip()}")


def _rpaths(path: Path) -> list[Path]:
    output = subprocess.run(["otool", "-l", str(path)], check=True,
                            capture_output=True, text=True).stdout
    found: list[Path] = []
    in_rpath = False
    for line in output.splitlines():
        stripped = line.strip()
        if stripped == "cmd LC_RPATH":
            in_rpath = True
        elif in_rpath and stripped.startswith("path "):
            value = stripped[5:].split(" (offset", 1)[0]
            found.append(Path(value))
            in_rpath = False
        elif stripped.startswith("cmd "):
            in_rpath = False
    return found


def _dependencies(path: Path) -> list[str]:
    output = subprocess.run(["otool", "-L", str(path)], check=True,
                            capture_output=True, text=True).stdout
    return [line.strip().split(" (compatibility version", 1)[0]
            for line in output.splitlines()[1:] if line.strip()]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_dependency(value: str, source: Path, executable_dir: Path) -> Path | None:
    if value.startswith(("/System/Library/", "/usr/lib/")):
        return None
    if value.startswith("@loader_path/"):
        target = source.parent / value.removeprefix("@loader_path/")
    elif value.startswith("@executable_path/"):
        target = executable_dir / value.removeprefix("@executable_path/")
    elif value.startswith("@rpath/"):
        suffix = value.removeprefix("@rpath/")
        candidates = [entry / suffix for entry in _rpaths(source)]
        candidates += [executable_dir / suffix]
        target = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
    else:
        target = Path(value)
    if not target.exists():
        raise RuntimeError(f"FFmpeg dependency cannot be resolved: {value} (from {source})")
    return target.resolve()


def bundle_ffmpeg_libraries(ffmpeg: Path, ffprobe: Path) -> None:
    """Copy Homebrew dylibs and rewrite load paths to stay inside FFmpeg's folder."""
    require("otool", "install the Xcode Command Line Tools")
    require("install_name_tool", "install the Xcode Command Line Tools")
    require("codesign", "install Xcode Command Line Tools")
    lib_dir = VENDOR_FFMPEG / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    executable_dir = ffmpeg.parent
    pending: list[tuple[Path, Path, bool]] = [
        (ffmpeg.resolve(), ffmpeg, False),
        (ffprobe.resolve(), ffprobe, False),
    ]
    visited: set[tuple[Path, Path]] = set()
    staged_hashes: dict[Path, str] = {}
    while pending:
        source, destination, is_library = pending.pop()
        source_real = source.resolve()
        visit_key = (source_real, destination)
        if visit_key in visited:
            continue
        visited.add(visit_key)
        changes: list[tuple[str, str]] = []
        dependencies = _dependencies(source_real)
        if is_library and dependencies:
            # otool prints a dylib's own LC_ID_DYLIB before its dependencies.
            dependencies = dependencies[1:]
        for dependency in dependencies:
            resolved = _resolve_dependency(dependency, source_real, executable_dir)
            if resolved is None:
                continue
            filename = Path(dependency).name
            staged = lib_dir / filename
            source_hash = _sha256(resolved)
            if staged.exists():
                if staged_hashes.get(staged, _sha256(staged)) != source_hash:
                    stem, suffix = Path(filename).stem, Path(filename).suffix
                    staged = lib_dir / f"{stem}.clipforge-{source_hash[:8]}{suffix}"
            if not staged.exists():
                shutil.copy2(resolved, staged)
                verify_arm64(staged)
                staged_hashes[staged] = source_hash
                pending.append((resolved, staged, True))
            replacement = (
                f"@loader_path/{staged.name}"
                if is_library else f"@loader_path/lib/{staged.name}"
            )
            changes.append((dependency, replacement))
        for old, new in changes:
            run(["install_name_tool", "-change", old, new, str(destination)], capture=True)
        if is_library:
            run(["install_name_tool", "-id", f"@loader_path/{destination.name}", str(destination)], capture=True)

    # A generated build must not retain a load reference back to the builder's
    # Homebrew installation. These checks also catch unexpected link layouts.
    for binary in (ffmpeg, ffprobe, *lib_dir.glob("*.dylib")):
        verify_arm64(binary)
        remaining = "\n".join(_dependencies(binary))
        if "/opt/homebrew/" in remaining or "/usr/local/Cellar/" in remaining:
            raise RuntimeError(f"Builder-local dylib path remains in {binary}:\n{remaining}")
    # install_name_tool invalidates Homebrew's signatures. Ad-hoc sign the
    # standalone toolchain so macOS will load the rewritten dylib graph during
    # local builds. A public app still needs a Developer ID application pass.
    for binary in (*lib_dir.glob("*.dylib"), ffprobe, ffmpeg):
        run(["codesign", "--force", "--sign", "-", "--timestamp=none", str(binary)], capture=True)


def _safe_license_text(ffmpeg: Path) -> tuple[str, str, str]:
    version = run([str(ffmpeg), "-version"], capture=True).stdout
    config = run([str(ffmpeg), "-buildconf"], capture=True).stdout
    license = run([str(ffmpeg), "-L"], capture=True).stdout
    if "version 3 or later" not in license and "GNU General Public License" not in license:
        raise RuntimeError("The staged FFmpeg license output was empty or unrecognized.")
    return version, config, license


def stage_ffmpeg(explicit_dir: Path | None) -> None:
    VENDOR_FFMPEG.mkdir(parents=True, exist_ok=True)

    def make_removable(function, path, _error) -> None:
        Path(path).chmod(0o700)
        function(path)

    shutil.rmtree(VENDOR_FFMPEG / "lib", onerror=make_removable)
    source_dir = explicit_dir
    sources: dict[str, Path] = {}
    for name in ("ffmpeg", "ffprobe"):
        candidate = source_dir / name if source_dir else Path(shutil.which(name) or "")
        if not candidate.is_file():
            raise RuntimeError(f"Could not find {name}; install a GPL FFmpeg build or pass --ffmpeg-dir.")
        verify_arm64(candidate)
        destination = VENDOR_FFMPEG / name
        destination.unlink(missing_ok=True)
        shutil.copy2(candidate, destination)
        destination.chmod(destination.stat().st_mode | 0o111)
        sources[name] = destination

    bundle_ffmpeg_libraries(sources["ffmpeg"], sources["ffprobe"])
    version, config, license = _safe_license_text(sources["ffmpeg"])
    encoders = run([str(sources["ffmpeg"]), "-hide_banner", "-encoders"], capture=True).stdout
    if "h264_videotoolbox" not in encoders:
        raise RuntimeError("FFmpeg does not include the required h264_videotoolbox encoder.")
    if "libx264" not in encoders:
        raise RuntimeError("FFmpeg must include libx264 as a software fallback encoder.")
    ffmpeg_sha = hashlib.sha256(sources["ffmpeg"].read_bytes()).hexdigest()
    ffprobe_sha = hashlib.sha256(sources["ffprobe"].read_bytes()).hexdigest()
    notice = (
        "FFmpeg for macOS ARM64\n"
        "======================\n\n"
        "This app bundles the FFmpeg and ffprobe executables below with their\n"
        "non-system dynamic libraries. FFmpeg is invoked as a separate process.\n\n"
        f"{version.strip()}\n\nBuild configuration:\n{config.strip()}\n\n"
        f"{license.strip()}\n\n"
        "Source and license information: https://ffmpeg.org/download.html\n"
        "Build recipe: system package-manager FFmpeg selected on the Apple\n"
        "Silicon build host; the exact configuration and executable SHA-256\n"
        "values are recorded here for this release.\n\n"
        f"ffmpeg SHA-256: {ffmpeg_sha}\nffprobe SHA-256: {ffprobe_sha}\n"
    )
    (VENDOR_FFMPEG / "README-FFMPEG.txt").write_text(notice, encoding="utf-8")


def make_icon() -> None:
    source = ROOT / "docs" / "whop-store" / "app-icon-512.png"
    output = ROOT / "ui" / "build" / "icon.icns"
    if not source.is_file():
        raise RuntimeError(f"Mac icon source is missing: {source}")
    run(["sips", "-s", "format", "icns", str(source), "--out", str(output)])


def smoke_backend() -> None:
    executable = BACKEND_OUT / "api"
    if not executable.is_file():
        raise RuntimeError(f"PyInstaller did not produce {executable}.")
    runtime_ffmpeg = BACKEND_OUT / "_internal" / "ffmpeg" / "ffmpeg"
    runtime_ffprobe = BACKEND_OUT / "_internal" / "ffmpeg" / "ffprobe"
    runtime_ollama = BACKEND_OUT / "_internal" / "ollama" / "ollama"
    if not runtime_ffmpeg.is_file() or not runtime_ffprobe.is_file():
        raise RuntimeError("The frozen backend is missing its bundled ffmpeg executable.")
    if not runtime_ollama.is_file():
        raise RuntimeError("The frozen backend is missing its bundled Ollama executable.")
    for runtime_binary in (runtime_ffmpeg, runtime_ffprobe, runtime_ollama):
        runtime_binary.chmod(runtime_binary.stat().st_mode | 0o111)
        verify_arm64(runtime_binary)
    verify_arm64(executable)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    with tempfile.TemporaryFile() as child_log:
        child = subprocess.Popen([str(executable), "serve", "--port", str(port)],
                                 cwd=ROOT, env=env, stdout=child_log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        failure: str | None = None
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    failure = f"Frozen backend exited during startup with code {child.returncode}."
                    break
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                        health = json.loads(response.read())
                    if health.get("ok") is True and isinstance(health.get("api_version"), int):
                        print(f"Frozen API health check passed (app {health.get('app_version')}).")
                        return
                except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
                    time.sleep(0.25)
            if failure is None:
                failure = "Frozen backend did not answer GET /health within 60 seconds."
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            child_log.seek(0)
            log_tail = child_log.read().decode("utf-8", errors="replace")[-5000:]
        if failure:
            raise RuntimeError(f"{failure}\nFrozen backend output:\n{log_tail}")


def check_host() -> None:
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise RuntimeError("Build this target on native Apple Silicon macOS (arm64), not under Rosetta.")
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError(f"Python 3.11 is required by the plugin runtime; found {platform.python_version()}.")
    try:
        import PyInstaller  # noqa: F401
        import torch
        import yaml  # noqa: F401
        import fastapi  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(f"Backend dependencies are missing ({exc}). Install requirements-macos.txt first.") from exc
    if not shutil.which("npm") or not shutil.which("node"):
        raise RuntimeError("Install Node.js and npm before building the Electron application.")
    if not (UI / "node_modules").is_dir():
        run(["npm", "ci"], UI)
    if shutil.disk_usage(ROOT).free < MIN_FREE_GB * 1_000_000_000:
        raise RuntimeError(f"At least {MIN_FREE_GB} GB free disk space is required for the one-dir backend and installers.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg-dir", type=Path,
                        help="directory containing ARM64 ffmpeg and ffprobe (defaults to PATH)")
    parser.add_argument("--skip-ffmpeg-stage", action="store_true",
                        help="reuse vendor/ffmpeg after it has been staged and reviewed")
    parser.add_argument("--skip-ollama-fetch", action="store_true",
                        help="reuse vendor/ollama after the pinned runtime has been fetched")
    parser.add_argument("--skip-backend", action="store_true",
                        help="reuse build/dist/backend after it passes the frozen health smoke test")
    args = parser.parse_args()
    try:
        check_host()
        if not args.skip_ffmpeg_stage:
            stage_ffmpeg(args.ffmpeg_dir)
        if not args.skip_ollama_fetch:
            run([sys.executable, str(ROOT / "scripts" / "fetch_ollama_macos.py")])
        if not (VENDOR_FFMPEG / "ffmpeg").is_file() or not (VENDOR_FFMPEG / "ffprobe").is_file():
            raise RuntimeError("FFmpeg is not staged. Run without --skip-ffmpeg-stage.")
        if not (VENDOR_FFMPEG / "README-FFMPEG.txt").is_file():
            raise RuntimeError("FFmpeg license notice is missing from vendor/ffmpeg.")
        if not (ROOT / "vendor" / "ollama" / "ollama").is_file():
            raise RuntimeError("Ollama is not staged. Run without --skip-ollama-fetch.")

        make_icon()
        if not args.skip_backend:
            shutil.rmtree(BACKEND_OUT, ignore_errors=True)
            run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
                 "--distpath", str(ROOT / "build" / "dist"),
                 "--workpath", str(ROOT / "build" / "work"),
                 str(ROOT / "clips-studio.spec")])
        else:
            print("Reusing the existing frozen backend; verifying it before packaging.")
        smoke_backend()
        run([sys.executable, str(ROOT / "scripts" / "generate_macos_sbom.py")])
        run(["npm", "run", "package:mac:arm64", "--", "--publish", "never"], UI)
        release = ROOT / "release"
        app_bundle = list(release.rglob("ClipForge.app"))
        dmgs = list(release.glob("ClipForge-*-arm64.dmg"))
        zips = list(release.glob("ClipForge-*-arm64.zip"))
        if not app_bundle or not dmgs or not zips:
            raise RuntimeError("Packaging finished without the expected .app, DMG, and ZIP outputs.")
        print("\nMac packaging complete:")
        for artifact in [app_bundle[0], *dmgs, *zips, ROOT / "build" / "macos-release" / "SBOM.json"]:
            print(f"  {artifact}")
        print("Signing/notarization are not enabled; this is an unsigned development build.")
        return 0
    except Exception as exc:
        print(f"macOS build failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
