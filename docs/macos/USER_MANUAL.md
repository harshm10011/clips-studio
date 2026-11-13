# ClipForge for macOS — user manual

## First launch

Open ClipForge and complete the setup wizard. It checks the local engine,
FFmpeg, Ollama, transcription weights, and disk space. Choose the suggested
local model or select a different Ollama model. Model downloads can take time
and several gigabytes; Ollama keeps its model files in the ClipForge data
folder. If setup is interrupted, open Settings and run setup again.

The core clipping workflow uses local models and does not need a paid AI API.
Internet access is needed to fetch a model or download supported public source
videos. Optional cloud providers and publishing integrations need their own
accounts and keys.

## Make clips

1. Choose **Import** to select a local video, or enter a supported public
   source URL.
2. Add more videos to the Processing Queue for batch work. The queue stores
   job settings and recovers interrupted jobs when the app starts again.
3. Review the ranked moments and their selection reasons in the clip library.
4. Open a clip in the editor to adjust its trim, caption text, format, and
   export settings.
5. Export the rendered MP4 to a folder you choose.

## Formats and captions

Choose vertical 9:16, square 1:1, or horizontal 16:9 in the editor. Captions
can be corrected and styled before export. H.264 is the default; H.265 is an
optional export choice when the bundled FFmpeg supports it. Apple VideoToolbox
is used for supported hardware encoding, with a software fallback.

## Queue and storage

Pause the queue to let the active video finish, cancel a running job, retry a
failed item, or reorder pending work. ClipForge caches source downloads,
transcripts, and analysis signals to reduce repeat work. Use Settings → Storage
to remove completed video data; exported files are separate and are not
deleted with a project.

## Local and optional services

The local Ollama model handles clip titles and scoring. Transcription uses
local Whisper weights. Supported public source adapters are subject to each
service's availability and access rules. Features that require cloud AI,
connected accounts, or publishing credentials are optional and are not part
of the no-paid-API core flow.
