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
- Local Whisper weights are dropped after transcription. A local Ollama model stays warm across queued videos while available memory is healthy and unloads after a run when estimated headroom is tight; remote Ollama hosts are never sent unload requests. Unused PyTorch cache is also cleared at the job boundary.
- FFmpeg is queried for VideoToolbox encoders. Whisper stays on CPU on MPS because the current faster-whisper/CTranslate2 backend has no MPS or Core ML path.
- Core ML is detected as a macOS system runtime. Python conversion tools and WhisperKit are reported separately; neither is installed in this environment, so no Core ML transcription path is claimed.
- Hardware report and pure-Python profile tests pass. Ollama is now staged, but no M4 inference benchmark has run: no local model has been downloaded, and the installed PyTorch build reports MPS unavailable.

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
- A packaged M4 end-to-end sample-video run has not been completed. M4 throughput and real source/video tests remain release validation.

## Prompt phase 05 — Professional macOS UI/UX

**Status: first Mac-first visual and interaction pass implemented; packaged UI review remains pending.**

- The existing Dashboard, creator and video libraries, import flow, live Processing Queue, AI/model controls, generated clips, clip and subtitle editors, export settings, diagnostics, and Settings remain connected to the real API and WebSocket job events.
- Replaced the blue-navy palette with shared graphite and violet tokens and moved system controls to the same accent token. The font stack now uses the native Apple system font where available.
- macOS uses the native inset traffic lights with a reserved title-bar gutter. The other desktop platforms retain their standard title bar.
- Added Command+1–8 navigation on macOS (Control+1–8 on Windows/Linux) in sidebar order, with the active destination exposed to assistive technology.
- UI dependencies are installed, and UI typecheck plus production build pass. Packaged M4 visual review remains pending.

## Prompt phase 06 — Automatic subtitles and video editor

**Status: editor and export extensions implemented; real render review remains pending.**

- The project already has 9:16 speaker tracking, 16:9 longform output, word-timed captions, Hindi/English transcription, caption corrections, manual trims, an exact render preview, FFmpeg output, and VideoToolbox H.264 selection with software fallback.
- Added a per-clip 1:1 square format. It renders at 1080×1080 with a centered crop; the editor labels that choice and keeps the preview, watermark, captions, and final render on the square canvas. Choose Vertical to use the existing AI speaker-tracking crop.
- Added caption templates plus controls for outline colour/width and a background box with colour/opacity. Added common macOS fonts and automatic macOS script-font choices for supported languages.
- Added H.265 MP4 export and selectable 4, 8, or 12 Mb/s encoding. macOS tries VideoToolbox first, then FFmpeg's libx265; default H.264 export still copies the already-rendered file.
- No M4 sample render has been reviewed. A later synthetic Phase 7 benchmark confirmed H.264 VideoToolbox encoding; H.265 hardware encoding still depends on the FFmpeg build and has not been exercised end to end.

## Prompt phase 07 — Batch processing and performance

**Status: durable batch workflow audited; macOS render limits, signal caching, and a VideoToolbox benchmark are implemented.**

- The existing SQLite queue stages multiple videos, enforces a five-job active cap, prevents duplicate queued/running videos, stores each job's settings, supports ordering, pause, cancellation, retry, and restart recovery, and reports per-job progress plus an overall time estimate.
- A single pipeline worker processes one video at a time. Interrupted jobs return to the queue, while completed downloads and transcripts are reused. Completed audio and visual feature arrays now have a versioned cache keyed by video ID and source path/size/mtime; stale entries are rebuilt, writes are atomic, and orphan entries are reclaimable in Storage cleanup.
- The local Ollama model remains warm between queued videos while memory headroom is normal, avoiding repeated model startup. It unloads after a run when available-memory estimates indicate tight or critical headroom.
- Apple Silicon rendering is capped at one clip render worker to preserve unified-memory headroom. Dashboard memory stats now show available memory and an estimated pressure band; the estimate uses available-memory thresholds and is not Apple's private pressure metric. Queue pause still lets the active video finish; the estimate does not forcibly interrupt an active job.
- Run `python scripts/benchmark_macos.py` for a synthetic VideoToolbox matrix at 720p and 1080p, with 5- and 15-second cases. Pass `--resolutions 720p,1080p,4k --lengths 5,15,30` for a larger matrix. The report measures encoder throughput and FFmpeg process RSS, not model inference or the full pipeline.
- The current environment is an M4 MacBook Air with 16 GB RAM and FFmpeg VideoToolbox H.264/H.265 encoders. A 720p synthetic 5/15-second run encoded at 235/363 fps (7.83×/12.11× real time); 1080p encoded at 161/206 fps (5.36×/6.88×). Peak FFmpeg process RSS was about 76/76 MB at 720p and 122 MB at 1080p. Synthetic patterns are easier to encode than real footage; representative creator media and full AI throughput still need separate measurement.

## Milestone 03 — Native macOS process and package

**Status: local ARM64 app, DMG, and ZIP built; unsigned package validation remains.**

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

## Prompt phase 08 — Final testing, packaging, and release

**Status: first local package produced; release validation remains incomplete.**

- Added `scripts/build_macos.py` for native ARM64 dependency checks, FFmpeg
  dynamic-library staging, Ollama staging, PyInstaller freezing, frozen API
  health smoke check, SPDX inventory generation, and Electron DMG/ZIP output.
- Installed Python 3.11 and runtime/build dependencies, staged FFmpeg and the
  checksum-verified universal Ollama runtime, built the frozen backend, and
  produced `release/mac-arm64/ClipForge.app` and
  `release/ClipForge-2.1.0-arm64.dmg`. The packaged backend `/health` smoke
  check passed. Electron Builder produced the ARM64 DMG and ZIP.
- The UI typecheck and production build passed. The generated SPDX inventory
  contains 218 dependency/runtime entries. The app bundle is ARM64, unsigned,
  and not notarized.
- A focused suite of 113 macOS, storage path, preflight, model setup/recovery,
  and job readiness/progress tests passed. DMG checksum verification and ZIP
  integrity checks also passed.
- Added a checksum-verified fetcher for the official universal macOS Ollama
  release. The Electron Mac config is standalone and does not inherit the
  upstream Windows updater feed.
- Packaged Mac startup now waits for `GET /health`, records backend logs, and
  stops bundled backend/Ollama process groups on quit. Setup and preflight
  already cover first model setup, retry, missing runtime/model reporting, and
  disk-space warnings.
- Added installation, user, troubleshooting, release notes, and third-party
  license documents under `docs/macos/`.
- Remaining before a stable release: finish ZIP validation and launch the
  packaged GUI; run packaged first-run model setup, missing-model recovery,
  low-disk, interrupted-job, long-video, batch-export, and no-paid-API
  end-to-end checks. The Mac update feed remains deliberately disabled. Review
  npm's 24 reported dependency audit advisories, then sign and notarize before
  public distribution.

## Current blockers

- The public fork `harshm10011/clips-studio` and `macos/m4-support` branch are created, and milestone pushes are working. The Git metadata lives at `/private/tmp/clipforge-source/.git` for this managed checkout.
- Python 3.11.18, Node 24.11.1, and npm 11.6.2 are installed. The macOS Python dependencies and UI packages are present in the local build environment; `pip check` passes. Python 3.14 remains unsuitable for the required frozen runtime.
- The frozen backend health check passes, and staged FFmpeg produced a 720p H.264 VideoToolbox sample. The installed PyTorch build reports MPS unavailable; real transcription, AI inference, and a complete sample render through the packaged app still need validation.
- The local app is an unsigned development preview, and Gatekeeper rejects it. The release config now requires Developer ID signing and notarization credentials before it starts a costly build; this Mac has no valid signing identity installed. Packaged first-run, recovery, disk-pressure, interrupted-job, long-video, batch, and no-paid-API workflows remain untested end to end. npm reported 24 dependency audit advisories; inspect before public distribution.
