# macOS Dependency Compatibility

Snapshot: 2026-11-13, source commit `8990e4aee8ee4a9e667fa3b15aba09d4036039b4`.

| Component | Current use | macOS status | Work needed |
|---|---|---|---|
| Electron 31 / React 18 / Vite | Desktop UI | Cross-platform stack; ARM64 DMG/ZIP targets are now configured | Complete native backend and asset staging. Keep the current Windows targets. |
| Python engine / FastAPI | API and processing pipeline | Python source is usable on macOS; `scripts/build_macos.py` now targets the promised Python 3.11 runtime | Install the clean Mac requirements, freeze on Apple Silicon, and run the frozen API health smoke check. |
| PyInstaller | Frozen backend | The spec excludes CUDA cuBLAS outside Windows and no longer requires NVIDIA telemetry on macOS | Confirm the frozen ARM64 backend and its runtime imports on a clean Mac. |
| PyTorch / Ultralytics | Vision and optional GPU inference | The current selection logic only enables CUDA, otherwise CPU | Detect and probe MPS explicitly. Preserve CPU fallback if MPS is missing or a model operation fails. |
| Faster-Whisper / CTranslate2 | Local transcription | CPU fallback is available; the current code's accelerated path is CUDA | Benchmark CPU first on M4. Evaluate MLX Whisper or a Core ML/WhisperKit bridge separately before claiming Apple acceleration. |
| Ollama | Local LLM | A checksum-verified fetcher now stages the official universal Darwin runtime; Electron stores models in ClipForge Application Support | Validate the staged runtime and first-run local model flow in a packaged app. |
| FFmpeg | Decode, edit, crop, subtitle, encode | The Mac build driver copies non-system dylibs and rewrites them to app-relative paths; it checks VideoToolbox H.264 and `libx264` fallback | Confirm the packaged encoder and filters on a clean Apple Silicon Mac and review GPL source notices. |
| `nvidia-cublas-cu12` | Faster-Whisper CUDA library | Already restricted to Windows by a requirements marker | Keep out of macOS environment and frozen app. |
| `nvidia-ml-py` | NVIDIA telemetry | Now excluded on macOS by a `sys_platform != "darwin"` requirement marker | Keep its optional import path safe. Diagnostics should not report an NVIDIA error on Apple Silicon. |
| `keyring` | Connected account credentials off Windows | Already included on non-Windows; core secrets use a permission-restricted file outside Windows | Decide whether macOS OAuth secrets should use Keychain; do not fall back to plaintext. |
| OpenCV / ONNX Runtime / RapidOCR | Video features and OCR | Python wheel and model compatibility must be verified for Python 3.11 ARM64 | Install from a clean macOS dependency set and exercise imports and the affected model paths before bundling. |
| Node.js/npm | Electron build | Host has Node 24.11.1; a separate Mac Electron Builder config is in place and excludes the Windows update feed | Install the lockfile dependencies and complete the native ARM64 DMG/ZIP build. |

## Build constraints

The app promises its plugin runtime as `APP_PYTHON = (3, 11)` in `sdk/python/clipskitty_sdk/host.py`. `scripts/build_installer.py` refuses to freeze with a different Python minor. The current machine only has Python 3.14.2, so it is not ready to build the application backend yet.

The Windows build fetches Windows FFmpeg, QuickJS, and Ollama assets and checks for CUDA-enabled PyTorch. Those steps must not be reused unchanged for a Mac build. `scripts/build_macos.py` stages the build-host's ARM64 FFmpeg and its non-system libraries, while `scripts/fetch_ollama_macos.py` verifies the pinned official macOS Ollama archive. The actual package still requires a native Python 3.11 environment and release review.

## Apple Silicon validation gates

- Confirm Python 3.11 ARM64 wheels for runtime dependencies before installing the full environment.
- Confirm the frozen backend launches from the `.app` resources folder with no Terminal working directory.
- Confirm Ollama starts from the bundled location and stores models under the same Application Support root as the Python engine.
- Probe VideoToolbox with the exact H.264 arguments used by production renders; keep the existing CPU retry path.
- Only enable MPS for model paths that pass a real M4 inference probe. Do not infer support from `torch.backends.mps.is_available()` alone.
- Keep API inference local by default. No paid cloud endpoint is required for the core workflow.
