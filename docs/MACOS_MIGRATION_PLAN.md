# ClipForge for Mac — Migration Plan

Target machine: Apple M4, 16 GB unified memory, ARM64.
Target product: a local-first macOS fork of Clips Kitty, with no paid AI API required for the core workflow.

## Milestone 01 — Audit and macOS foundations

**Status: audit complete; portability and packaging changes started.** See [REPOSITORY_AUDIT.md](REPOSITORY_AUDIT.md) and [DEPENDENCY_COMPATIBILITY.md](DEPENDENCY_COMPATIBILITY.md).

- Preserve the upstream engine and Windows build while isolating macOS behavior.
- Use `macos/m4-support` for port work and retain the upstream remote.
- Move installed macOS data and editable settings into `~/Library/Application Support/ClipForge`.
- Select native ARM64 backend and Ollama executables from Electron.
- Add an ARM64 DMG/ZIP target to Electron Builder; finish the backend and dependency staging script before calling the package build complete.
- Split dependency fetching and packaging by platform.
- Add macOS checks to the existing deterministic test suite.

## Milestone 02 — M4 runtime and AI

- Report ARM64 architecture, unified memory, MPS availability, Ollama status, FFmpeg encoders, and free disk space.
- Keep one heavyweight inference job at a time on the 16 GB machine.
- Keep the working CPU transcription path while benchmarking local Apple-native options (MLX Whisper or a Core ML bridge).
- Enable MPS only for model paths that pass real inference checks; use CPU fallback and show the reason when it cannot run.
- Avoid downloading or loading multiple large models at once; release model resources after each job.

## Milestone 03 — Native macOS process and package

- Build the Python 3.11 backend for ARM64 with PyInstaller on macOS.
- Bundle ARM64 FFmpeg, QuickJS, Ollama, model assets, and required notices with separate pinned fetchers.
- Start and stop the backend and Ollama cleanly from Electron; support cancellation and recovery.
- Produce `ClipForge.app`, a DMG, and a ZIP. Keep signing/notarization as a later release decision because it requires Apple distribution credentials.
- Add startup health checks and diagnostics for missing binaries, models, permissions, and disk space.

## Milestone 04 — Usable first clip

Preserve the existing UI and pipeline first. The first end-to-end milestone is:

1. Import a permitted video URL or a local file.
2. Transcribe and analyze it locally.
3. Review ranked clip candidates.
4. Render a 9:16 clip with captions through FFmpeg/VideoToolbox, with software fallback.
5. Edit and export the MP4 locally.

After this works reliably, polish the Mac-first onboarding, model manager, settings, and clip review flow.

## Milestone 05 — Feature parity and release readiness

- Preserve creator profiles, batch processing, subtitles, clip editing, project history, gaming/sports modes, multilingual tools, and supported publishing flows.
- Make features that depend on Windows-only packaging or services explicit until their macOS implementations pass validation.
- Test long media, interrupted jobs, memory pressure, Apple Silicon rendering, and first-run model setup.
- Document source access limitations and keep local-file import available.
- Retain AGPL-3.0-or-later and all bundled third-party license notices.

## Current blockers

- The public fork `harshm10011/clips-studio` and its `macos/m4-support` branch are created. The local Git metadata is outside the workspace because this managed checkout does not permit `.git` writes.
- GitHub CLI is absent; `origin` and `upstream` are configured in the local Git checkout.
- Python 3.11, pytest, project Python dependencies, UI `node_modules`, and Ollama are not installed. Python 3.14.2 is present and cannot be used for the promised frozen runtime build.
- The macOS package, Apple inference paths, and rendering pipeline have not been built or exercised yet.
