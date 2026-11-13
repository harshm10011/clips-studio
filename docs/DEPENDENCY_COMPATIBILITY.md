# macOS Dependency Compatibility

Snapshot: 2026-11-13, source commit `8990e4aee8ee4a9e667fa3b15aba09d4036039b4`.

| Component | Current use | macOS status | Work needed |
|---|---|---|---|
| Electron 31 / React 18 / Vite | Desktop UI | Cross-platform stack; ARM64 DMG/ZIP targets are now configured | Complete native backend and asset staging. Keep the current Windows targets. |
| Python engine / FastAPI | API and processing pipeline | Python source is usable on macOS, but the frozen build flow is Windows-specific | Freeze on an Apple Silicon Mac with the promised Python 3.11 runtime; package a native `api` executable. |
| PyInstaller | Frozen backend | Can build for the host OS/architecture; the spec now excludes the CUDA 12 cuBLAS payload outside Windows | Add a macOS build driver and smoke-test the frozen ARM64 backend. |
| PyTorch / Ultralytics | Vision and optional GPU inference | The current selection logic only enables CUDA, otherwise CPU | Detect and probe MPS explicitly. Preserve CPU fallback if MPS is missing or a model operation fails. |
| Faster-Whisper / CTranslate2 | Local transcription | CPU fallback is available; the current code's accelerated path is CUDA | Benchmark CPU first on M4. Evaluate MLX Whisper or a Core ML/WhisperKit bridge separately before claiming Apple acceleration. |
| Ollama | Local LLM | App can use an external Ollama in development; the packaged app bundles only Windows AMD64 | Add a pinned macOS ARM64 runtime fetch/build input and update Electron's executable path. Keep model files in the app's data directory. |
| FFmpeg | Decode, edit, crop, subtitle, encode | `video/encoding.py` already probes `h264_videotoolbox`; the local FFmpeg 9.0.2 has VideoToolbox enabled | Bundle a compatible macOS ARM64 build and verify the exact filters and encoders used by renders. Retain software encoding fallback. |
| `nvidia-cublas-cu12` | Faster-Whisper CUDA library | Already restricted to Windows by a requirements marker | Keep out of macOS environment and frozen app. |
| `nvidia-ml-py` | NVIDIA telemetry | Now excluded on macOS by a `sys_platform != "darwin"` requirement marker | Keep its optional import path safe. Diagnostics should not report an NVIDIA error on Apple Silicon. |
| `keyring` | Connected account credentials off Windows | Already included on non-Windows; core secrets use a permission-restricted file outside Windows | Decide whether macOS OAuth secrets should use Keychain; do not fall back to plaintext. |
| OpenCV / ONNX Runtime / RapidOCR | Video features and OCR | Python wheel and model compatibility must be verified for Python 3.11 ARM64 | Install from a clean macOS dependency set and exercise imports and the affected model paths before bundling. |
| Node.js/npm | Electron build | Host has Node 24.11.1; the repository documents Node 18+ | Use the lockfile and confirm the supported Node range on CI; do not silently change Electron dependencies during the port. |

## Build constraints

The app promises its plugin runtime as `APP_PYTHON = (3, 11)` in `sdk/python/clipskitty_sdk/host.py`. `scripts/build_installer.py` refuses to freeze with a different Python minor. The current machine only has Python 3.14.2, so it is not ready to build the application backend yet.

The Windows build fetches Windows FFmpeg, QuickJS, and Ollama assets and checks for CUDA-enabled PyTorch. Those steps must not be reused unchanged for a Mac build. Build inputs must be selected by platform and architecture, pinned, and accompanied by their license notices.

## Apple Silicon validation gates

- Confirm Python 3.11 ARM64 wheels for runtime dependencies before installing the full environment.
- Confirm the frozen backend launches from the `.app` resources folder with no Terminal working directory.
- Confirm Ollama starts from the bundled location and stores models under the same Application Support root as the Python engine.
- Probe VideoToolbox with the exact H.264 arguments used by production renders; keep the existing CPU retry path.
- Only enable MPS for model paths that pass a real M4 inference probe. Do not infer support from `torch.backends.mps.is_available()` alone.
- Keep API inference local by default. No paid cloud endpoint is required for the core workflow.
