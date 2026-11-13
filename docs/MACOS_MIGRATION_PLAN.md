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

**Status: first implementation complete; real MPS/Core ML runtime validation remains pending.**

- Added `core/macos` hardware, acceleration, memory-profile, and local Ollama diagnostics, plus `scripts/diagnose_macos.py`.
- PyTorch device selection now prefers MPS, validates YOLO accelerators with a small real inference, and retries on CPU when a model cannot run. Local transcription, Ollama and vision inference share one heavy AI slot.
- A 16 GB profile recommends the repository's tested `gemma3:4b` and limits one heavy AI job at a time. The recommendation does not overwrite the user's model setting.
- Local Whisper weights are dropped after transcription. On machines at or below 24 GB, a locally hosted Ollama model is asked to unload after each completed video; remote Ollama hosts are never sent unload requests. Unused PyTorch cache is also cleared at the job boundary.
- FFmpeg is queried for VideoToolbox encoders. Whisper stays on CPU on MPS because the current faster-whisper/CTranslate2 backend has no MPS or Core ML path.
- Core ML is detected as a macOS system runtime. Python conversion tools and WhisperKit are reported separately; neither is installed in this environment, so no Core ML transcription path is claimed.
- Hardware report and pure-Python profile tests pass. No M4 inference benchmark has run yet because Ollama and an MPS-enabled PyTorch build are absent.

- Report ARM64 architecture, unified memory, MPS availability, Ollama status, FFmpeg encoders, and free disk space.
- Keep one heavyweight inference job at a time on the 16 GB machine.
- Keep the working CPU transcription path while benchmarking local Apple-native options (MLX Whisper or a Core ML bridge).
- Enable MPS only for model paths that pass real inference checks; use CPU fallback and show the reason when it cannot run.
- Avoid downloading or loading multiple large models at once; release model resources after each job.

## Prompt phase 03 — Multi-creator source manager

**Status: existing source workflows audited; direct creator setup added.**

- The app already has YouTube, Twitch, and Kick source adapters, watched-channel discovery, local file import, a deduplicating processing queue, job history, and creator video/clip libraries.
- The Creators screen can now create a named profile from a public channel URL, handle, or platform ID. It uses the existing platform resolver and refuses to silently take a channel that belongs to another profile.
- Watched-channel setup remains the workflow for ongoing discovery. A profile created here is a library identity; it does not start polling or processing on its own.
- Source access is limited to what each platform adapter can read. Private, removed, unavailable, or unsupported sources keep their source error; local file import remains available as a fallback. No DRM or access-control bypass is added.
- The profile setup API and UI are implemented, but macOS runtime behavior and full source-access coverage still need validation on the packaged app.

## Prompt phase 04 — AI highlight detection and clip generation

**Status: core pipeline audited; selection rationale now reaches the clip library.**

- The existing pipeline extracts timestamped word-level transcripts, caches them per video, and scores transcript candidates together with audio, visual, reaction, and optional audience signals. It uses transcript context and sentence-aware timing rather than keyword-only selection.
- Candidates are checked for minimum score, duplicates, overlap, segment reuse, and configured duration limits; surviving moments are ranked, titled, described, captioned, and rendered through FFmpeg.
- The pipeline already checks cancellation during transcription, analysis, and rendering, retries malformed model output once, and reuses downloaded media and cached transcripts on a rerun.
- Candidate `reason` text was generated but not saved with the clip. It is now persisted with the score details and shown in Clip Studio and the editor.
- The default duration configuration is 10–60 seconds, with sentence fitting growing short picks toward a watchable length; the existing 60s+ option selects 61–180 seconds. Specific clips can use the existing long-form modes.
- This environment lacks pytest, FastAPI, and UI dependencies, so no packaged end-to-end sample-video run is claimed. M4 throughput and real source/video tests remain release validation.

## Prompt phase 05 — Professional macOS UI/UX

**Status: first Mac-first visual and interaction pass implemented; packaged UI review remains pending.**

- The existing Dashboard, creator and video libraries, import flow, live Processing Queue, AI/model controls, generated clips, clip and subtitle editors, export settings, diagnostics, and Settings remain connected to the real API and WebSocket job events.
- Replaced the blue-navy palette with shared graphite and violet tokens and moved system controls to the same accent token. The font stack now uses the native Apple system font where available.
- macOS uses the native inset traffic lights with a reserved title-bar gutter. The other desktop platforms retain their standard title bar.
- Added Command+1–8 navigation on macOS (Control+1–8 on Windows/Linux) in sidebar order, with the active destination exposed to assistive technology.
- UI dependencies are not installed here, so the packaged M4 visual review and build are still pending.

## Prompt phase 06 — Automatic subtitles and video editor

**Status: editor and export extensions implemented; real render review remains pending.**

- The project already has 9:16 speaker tracking, 16:9 longform output, word-timed captions, Hindi/English transcription, caption corrections, manual trims, an exact render preview, FFmpeg output, and VideoToolbox H.264 selection with software fallback.
- Added a per-clip 1:1 square format. It renders at 1080×1080 with a centered crop; the editor labels that choice and keeps the preview, watermark, captions, and final render on the square canvas. Choose Vertical to use the existing AI speaker-tracking crop.
- Added caption templates plus controls for outline colour/width and a background box with colour/opacity. Added common macOS fonts and automatic macOS script-font choices for supported languages.
- Added H.265 MP4 export and selectable 4, 8, or 12 Mb/s encoding. macOS tries VideoToolbox first, then FFmpeg's libx265; default H.264 export still copies the already-rendered file.
- UI dependencies are absent here, and no M4 sample render or hardware encoder run has been performed. H.265 availability depends on the FFmpeg build; the export path reports an error if neither the hardware nor software encoder is available.

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
- Python 3.11, pytest, most project Python dependencies, UI `node_modules`, Ollama, `coremltools`, and WhisperKit are not installed. Python 3.14.2 is present and cannot be used for the promised frozen runtime build.
- This environment's PyTorch reports MPS unavailable. The MPS path has mocked coverage, but real Apple inference and end-to-end rendering still need an MPS-enabled dependency build.
- The macOS package and production rendering pipeline have not been built or exercised yet.
