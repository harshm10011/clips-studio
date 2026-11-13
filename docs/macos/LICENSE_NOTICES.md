# Third-party license notices for ClipForge on macOS

ClipForge itself is licensed under AGPL-3.0-or-later; the full license is
included beside the app. The Python SDK is MIT-licensed and its license is
included in the frozen backend. Consult each bundled component's own notice
and the generated `SBOM.json` for the exact release build.

## Runtime components

- **FFmpeg and ffprobe:** the build records the exact version, build
  configuration, license output, and executable SHA-256 in
  `README-FFMPEG.txt`. The configured build includes GPL components such as
  libx264 and is distributed as a separate executable. Corresponding source
  and license information: <https://ffmpeg.org/download.html>.
- **Ollama:** MIT License. The checksum-pinned upstream runtime is accompanied
  by `README-OLLAMA.txt` and any upstream notice files.
- **Python and JavaScript dependencies:** package metadata and versions are
  listed in the generated SPDX inventory. Each package retains its own
  copyright and license terms.
- **Model weights:** model weights downloaded during setup are not bundled in
  the preview DMG; their provider terms apply separately.

The build inventory records metadata hints. Release owners must review the
actual packaged dependency tree and satisfy any source-offer, attribution, or
redistribution obligations before publishing.
