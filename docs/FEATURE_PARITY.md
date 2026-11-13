# macOS Feature Parity

The source already contains most product features. The macOS project should preserve them and adapt the operating-system integration around them rather than start over.

| Feature area | Existing source capability | macOS port status / first parity target |
|---|---|---|
| Sources | YouTube, Twitch, Kick, and local video workflows | Preserve supported authorized sources; keep local import as fallback when access is unavailable. |
| Creators and projects | Creator profiles, creator knowledge, project/job state, and processing history | Keep the Python API and SQLite data model; use a stable macOS Application Support directory. |
| Transcription and analysis | Faster-Whisper, multimodal signals, LLM scoring, clip candidates, titles, descriptions, and hashtags | Run locally first with CPU fallback; benchmark M4 acceleration before enabling it. |
| Clip rendering | FFmpeg editing, 9:16 crop, speaker tracking, caption burn-in, and VideoToolbox probing | Bundle ARM64 FFmpeg; validate production filters and retain CPU/software encoder fallback. |
| Editing and export | Clip editor, trims/cuts, audio controls, captions, overlays, and MP4 export | Preserve existing UI and API; verify file dialogs, paths, and exported media on macOS. |
| Batch jobs | SQLite-backed queue, progress events, cancellation/retry paths, and workers | Preserve the job engine; test process shutdown and resume behavior under macOS. |
| Local AI | Ollama model management and local inference | Bundle a macOS ARM64 runtime and align its model directory with the backend's data root. |
| Gaming and sports | Specialized analysis, OCR, vision signals, and framing | Keep feature modules; make model availability and fallback behavior visible on Apple Silicon. |
| Multilingual | Translation, subtitles, and local TTS/dubbing | Preserve the pipeline; validate ARM64 model dependencies and voice downloads. |
| Publishing and automation | YouTube publishing, integrations, scheduled work, and watched channels | Preserve API-based features where supported; validate macOS credentials, permissions, and lifecycle behavior. |
| Remote rendering | Remote worker and render gateway | Retain as an optional feature; it is not required for the first local Mac clip. |
| Desktop packaging | Windows installer, tray support, updater, and Microsoft Store package | ARM64 DMG/ZIP targets are configured. The native backend and dependency staging flow still need implementation. Keep Windows packaging intact. |

## First parity gate

The first Mac milestone is complete only when a user can add a permitted source or local file, run local transcription and clip analysis, review candidates, render a captioned vertical MP4, and export it without opening Terminal for normal use. Full feature parity follows this gate.
