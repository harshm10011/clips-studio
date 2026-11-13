# ClipForge for macOS — development preview

This preview carries the first Mac-focused implementation across the existing
creator library, local clipping pipeline, editor, captions, batch queue, and
Apple Silicon resource controls.

## Included

- Native ARM64 Electron target with a one-directory frozen Python backend.
- Apple Silicon FFmpeg staging with VideoToolbox H.264 and `libx264` fallback
  checks, plus bundled dynamic libraries and FFmpeg license details.
- A checksum-pinned Ollama runtime and first-run local model setup.
- Startup health polling, backend and Ollama logs, and process-group shutdown
  for packaged Mac children.
- Vertical, square, and horizontal exports, caption styles, and local batch
  processing.
- A release-time SPDX inventory and packaged installation, user, and
  troubleshooting documents.

## Build verification

- The Python UI typecheck and production UI build pass.
- 113 focused tests pass for macOS hardware and memory helpers, storage paths,
  first-run preflight, local model setup/recovery, and job readiness/progress.
- The frozen backend `/health` smoke check passed, and the bundled FFmpeg
  produced a 720p H.264 VideoToolbox sample.
- `hdiutil verify` validated the DMG checksum, and `unzip -t` found no errors
  in the ZIP archive.

## Known gaps

- A local ARM64 `.app`, DMG, and ZIP have been produced.
- The app is ad-hoc/unsigned and is not notarized. This Mac's distribution
  assessment rejects it; this preview is not safe to distribute or install.
- No end-to-end local video render, model recovery, insufficient-disk,
  interrupted-job, long-video, or batch export run has been completed on the
  packaged app. The frozen backend's `/health` smoke check passed, but the
  Electron GUI has not yet been launched as a packaged app.
- Automatic Mac updates are disabled pending a ClipForge-specific feed.
- Code signing and notarization require Apple Developer credentials and are
  still outstanding.
- CPU transcription is the supported baseline. MPS vision inference and
  VideoToolbox encoding have synthetic or code-path evidence, but need a
  packaged end-to-end review.
- `npm ci` reported 24 dependency audit advisories across the installed tree;
  review and resolve applicable production findings before public distribution.

This build is not marked stable.
