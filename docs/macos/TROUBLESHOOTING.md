# ClipForge for macOS — troubleshooting

## The app says its local engine is not ready

Quit and reopen ClipForge. The engine log is at
`~/Library/Application Support/ClipForge/logs/backend.log`; Ollama logs are in
the same folder as `ollama.log`. The app waits for `GET /health` before showing
the main window. If it still times out, check that another process is not
using local port 8765 and collect the log files for a bug report.

## Setup reports missing FFmpeg or Ollama

Use a complete ClipForge DMG build. A source checkout does not include the
Mac runtime binaries automatically. In a developer build, run
`python scripts/build_macos.py` to stage the pinned runtime and the FFmpeg
build with its required dylibs and license notice.

## A model is missing or its download stopped

Open Settings and choose **Run setup again**. Retry the model pull while online.
Ollama retains resumable partial model downloads; stale partials older than a
week are cleaned on app start. A model name in Settings must match a model
installed in Ollama.

## The first video needs more disk space

The preflight check warns below 20 GB free. Downloads, Whisper weights, model
files, source media, and exports can each use multiple gigabytes. Free space
and run setup again. Generated MP4 files are not removed by Storage cleanup.

## A job stopped or ClipForge closed during processing

The durable queue returns interrupted jobs to the pending state on the next
launch. Retry the item if it does not restart. Completed downloads and cached
transcripts are reused when possible. Do not delete the Application Support
folder while the app is open.

## Hardware acceleration is unavailable

H.264 may fall back from VideoToolbox to `libx264`. Compatible vision models
can use PyTorch MPS; transcription still uses the CPU path. The UI can continue
to process on CPU, but some jobs will take longer. H.265 depends on the exact
FFmpeg build and is not promised by every preview package.

## Updates, Gatekeeper, and release signing

Automatic updates are disabled for macOS builds until ClipForge has a separate
Mac feed. Do not install an update from the upstream Windows channel. Current
local builds are unsigned; a public DMG must be Developer ID signed,
notarized, stapled, and tested on a clean Mac before distribution.
