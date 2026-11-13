# macOS Repository Audit

Audit date: 2026-11-13
Source: `ColinGPT9/clips-studio`, branch `main`, commit `8990e4aee8ee4a9e667fa3b15aba09d4036039b4`
Working branch: `macos/m4-support`

## Product and architecture

The repository is the current Clips Kitty application (formerly Clips Studio), not a small starter project. It contains a mature clipping pipeline and a desktop app. The main components are:

- Electron 31, React 18, TypeScript, and Vite in `ui/`.
- A Python 3.11 frozen backend, with FastAPI, WebSockets, SQLite-backed jobs, and the media pipeline.
- Local Ollama inference, Faster-Whisper transcription, PyTorch/Ultralytics vision, and FFmpeg rendering.
- YouTube, Twitch, Kick, local-file, creator, editing, subtitle, export, publishing, sports, gaming, multilingual, and remote-render features.

`ARCHITECTURE.md` documents the actual system. The Electron UI talks to the local FastAPI service over HTTP and WebSockets; the service orchestrates the source, transcription, analysis, render, and metadata stages.

## Current platform support

The audited application ships for Windows. `CONTRIBUTING.md` explicitly describes Linux and macOS as development hosts for a Windows-only app. At the audited commit, `ui/electron-builder.yml` defined Windows NSIS/ZIP and Microsoft Store packaging only. This port has since added ARM64 DMG/ZIP targets; `scripts/build_installer.py` remains Windows-only and the native macOS backend staging flow is not implemented yet.

Several backend pieces are already portable or have useful fallbacks:

- `video/encoding.py` already probes FFmpeg encoders and includes Apple VideoToolbox before the CPU encoder fallback.
- `core/secrets.py` already uses a restricted-permission file store off Windows.
- The Electron process shutdown code uses `taskkill` on Windows and `child.kill()` elsewhere.
- `requirements.txt` already marks the CUDA 12 cuBLAS package as Windows-only and installs `keyring` off Windows.

The earlier idea that VideoToolbox encoding still needed to be invented was stale. The remaining work is packaging, data paths, runtime selection, and validating the Apple acceleration paths.

## macOS blockers found in source

1. **Installed data paths.** At the audited commit, `core/paths.py` sent every frozen non-override install to `LOCALAPPDATA` or `~/AppData/Local`. A macOS app needs a user-writable Application Support directory. `user_config_path()` repeated the same Windows fallback; the port now adds the macOS location.
2. **Bundled executables.** At the audited commit, `ui/src/main/index.ts` started `backend/api.exe` and `_internal/ollama/ollama.exe`. The port now selects native executable names, but the ARM64 payload is not built yet.
3. **Ollama acquisition.** `scripts/fetch_ollama.py` downloads the Windows AMD64 archive only. Its version and license notice are pinned and should be retained when adding a macOS ARM64 fetch path.
4. **Packaging.** `scripts/build_installer.py` remains Windows-only. The PyInstaller spec now collects CUDA assets only on Windows; the Mac build driver, native dependencies, and frozen backend checks remain to be implemented.
5. **AI acceleration.** `core/gpu.py` only chooses CUDA or CPU. `video/tracker.py` and `core/preflight.py` use that CUDA decision. Faster-Whisper's CTranslate2 path has a CPU fallback but no Apple MPS/Core ML implementation.
6. **Diagnostics.** GPU advice is NVIDIA-specific. The app should report Apple Silicon, memory, Ollama, MPS/Core ML, and VideoToolbox availability without treating absent NVIDIA hardware as a problem.
7. **Release integration.** Existing CI and release scripts focus on Linux/Windows checks and Windows packaging. There is no ARM64 macOS package job or signing/notarization setup.

## Preserved features and constraints

The port should extend the existing engine rather than rebuild it. Existing creator management, source adapters, local video imports, transcript-based analysis, candidate ranking, vertical rendering, captions, editing, batch jobs, and project state are the parity foundation. Source access remains subject to platform terms, authorization, authentication, and copyright; local import remains the fallback when a source cannot be acquired.

The repository is licensed `AGPL-3.0-or-later`. Keep the upstream license and notices, and review the source-sharing obligations before distributing a modified app.

## Local machine baseline

- MacBook Air, Apple M4, 16 GB unified memory, ARM64.
- macOS 26.6.2.
- Python 3.14.2 is the default Python; Python 3.11 is not installed. The project build script requires the exact Python minor version declared as `APP_PYTHON` (3.11).
- Node.js 24.11.1 and npm 11.6.2 are present. The UI dependencies are not installed in this checkout.
- FFmpeg 9.0.2 is installed with VideoToolbox support.
- Homebrew 7.0.12 and Git 2.50.1 are present. GitHub CLI and Ollama are not installed.
- Baseline pytest could not start: `python3 -m pytest -q` reports `No module named pytest`. No app tests have run yet.

## Initial implementation order

1. Make frozen data and settings paths correct on macOS while preserving Windows behavior.
2. Add focused path coverage for macOS and retain existing Windows path coverage.
3. Make Electron's packaged backend and Ollama executable paths platform-aware.
4. Split macOS ARM64 dependencies and packaging from the Windows CUDA installer.
5. Add Apple Silicon diagnostics and acceleration behind tested fallbacks.
6. Build and exercise the first local `.app`/DMG on the M4 before expanding parity.

## Portability changes started

- Frozen data and settings now use `~/Library/Application Support/ClipForge` on macOS while keeping the existing Windows directory.
- Electron selects `api` and `ollama` on macOS/Linux and keeps `api.exe` and `ollama.exe` on Windows. Ollama model and log paths now align with the Python backend's data root.
- Electron Builder has an Apple Silicon DMG/ZIP target. The backend staging/build driver is still outstanding.
- The PyInstaller spec now collects NVIDIA cuBLAS only on Windows, and the requirements exclude NVIDIA telemetry on macOS.
- A focused macOS path test was added. Its manual smoke check passed; pytest is unavailable in the current environment.
