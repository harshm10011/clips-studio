# ClipForge for macOS — installation and build

## Release status

This is a development preview. No signed or notarized ClipForge DMG has been
published yet. The Mac update feed is disabled until the fork has its own
release channel. Do not describe this build as stable.

## Build on Apple Silicon

Build on a native ARM64 Mac with Xcode Command Line Tools, Node.js/npm, Python
3.11, and at least 30 GB of free disk space. Python 3.11 is required by the
plugin runtime. Use a clean virtual environment so the generated inventory
matches the build environment:

```sh
python3.11 -m venv .venv-macos
source .venv-macos/bin/activate
python -m pip install --upgrade pip
python -m pip install --index-url https://pypi.org/simple -r requirements-macos.txt
cd ui && npm ci && cd ..
python scripts/build_macos.py
```

The build stages Apple Silicon FFmpeg and its non-system dynamic libraries,
fetches the checksum-pinned Ollama release, freezes the Python engine, checks
the frozen `/health` endpoint, creates the application icon, generates an
SPDX inventory, then packages the ARM64 app, DMG, and ZIP under `release/`.
FFmpeg can come from `PATH` or a directory passed with `--ffmpeg-dir`.

The builder exits when prerequisites are missing. It needs `ffmpeg` and
`ffprobe` with VideoToolbox H.264 and `libx264`, the pinned Ollama runtime,
Python 3.11 backend dependencies, and the complete UI dependency install.

## Install a built DMG

1. Open `ClipForge-<version>-arm64.dmg`.
2. Drag `ClipForge.app` to Applications.
3. Eject the mounted image, then open ClipForge from Applications.
4. Follow the first-run wizard. The wizard checks FFmpeg, Ollama, model setup,
   and available disk space. The recommended local language model is fetched
   on first use and stored under `~/Library/Application Support/ClipForge`.

Current developer builds are unsigned. macOS may block opening them; a public
release requires a Developer ID signature, hardened-runtime entitlements,
notarization, stapling, and a clean install test on a second Mac. Apple
distribution credentials are not part of this repository.

## Data and permissions

ClipForge uses ordinary macOS app permissions and opens files/folders through
native pickers. It does not request microphone or camera access. Imported
source videos, local models, generated clips, queue state, and logs are kept
under `~/Library/Application Support/ClipForge`; exports go to the folder you
choose. Quit the app before moving or deleting that data.
