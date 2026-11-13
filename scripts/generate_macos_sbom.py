"""Generate a release-time SPDX inventory for the macOS build environment."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def normalize_license(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict) and isinstance(value.get("type"), str):
        return value["type"]
    return "NOASSERTION"


def package_id(prefix: str, name: str, version: str) -> str:
    slug = "".join(ch if ch.isalnum() else "-" for ch in f"{prefix}-{name}-{version}")
    return "SPDXRef-" + slug[:100]


def license_hint(metadata: importlib.metadata.Distribution) -> str:
    value = metadata.metadata.get("License")
    if value and value.strip().lower() not in {"unknown", "unspecified"}:
        return value.strip()
    for classifier in metadata.metadata.get_all("Classifier", []):
        if classifier.startswith("License :: OSI Approved :: "):
            return classifier.rsplit(" :: ", 1)[-1]
    return "NOASSERTION"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def npm_packages() -> list[dict]:
    lock = json.loads((ROOT / "ui" / "package-lock.json").read_text(encoding="utf-8"))
    result = []
    for path, details in lock.get("packages", {}).items():
        # Electron is a development dependency in package.json, but the
        # Electron Framework is part of the shipped .app runtime.
        bundled_electron = path == "node_modules/electron"
        if not path or (details.get("dev", False) and not bundled_electron):
            continue
        name = details.get("name") or path.rsplit("node_modules/", 1)[-1]
        if not details.get("version"):
            continue
        result.append({
            "name": name,
            "version": details["version"],
            "license": normalize_license(details.get("license")),
            "downloadLocation": details.get("resolved") or "NOASSERTION",
            "integrity": details.get("integrity"),
            "scope": "Bundled Electron runtime" if bundled_electron else "Production npm dependency",
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "macos-release" / "SBOM.json")
    args = parser.parse_args()

    packages = []
    runtime = importlib.metadata.distributions()
    for distribution in runtime:
        name = distribution.metadata.get("Name")
        version = distribution.version
        if not name or not version:
            continue
        packages.append({
            "name": name,
            "version": version,
            "license": license_hint(distribution),
            "downloadLocation": "NOASSERTION",
            "scope": "Python build environment",
        })
    packages.append({
        "name": "Python",
        "version": platform.python_version(),
        "license": "Python-2.0",
        "downloadLocation": "https://www.python.org/",
        "scope": "Frozen Python runtime",
    })

    sbom_packages = []
    for entry in packages + npm_packages():
        item = {
            "SPDXID": package_id("Package", entry["name"], entry["version"]),
            "name": entry["name"],
            "versionInfo": entry["version"],
            "downloadLocation": entry.get("downloadLocation") or "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": entry.get("license") or "NOASSERTION",
            "copyrightText": "NOASSERTION",
            "primaryPackagePurpose": "APPLICATION",
            "comment": entry.get("scope", "Production npm dependency"),
        }
        integrity = entry.get("integrity", "")
        if "-" in integrity:
            algorithm, encoded = integrity.split("-", 1)
            if algorithm in {"sha1", "sha256", "sha384", "sha512"}:
                item["checksums"] = [{
                    "algorithm": algorithm.upper(),
                    "checksumValue": base64.b64decode(encoded).hex(),
                }]
        sbom_packages.append(item)

    binary_roots = [ROOT / "vendor" / "ffmpeg", ROOT / "vendor" / "ollama"]
    binary_files = [path for base in binary_roots if base.is_dir()
                    for path in base.rglob("*") if path.is_file()]
    for path in binary_files:
        relative = path.relative_to(ROOT)
        if path.is_file():
            sbom_packages.append({
                "SPDXID": package_id("Binary", str(relative), sha256(path)[:12]),
                "name": str(relative),
                "versionInfo": "NOASSERTION",
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION",
                "checksums": [{"algorithm": "SHA256", "checksumValue": sha256(path)}],
                "primaryPackagePurpose": "FILE",
            })

    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "ClipForge macOS ARM64 release inventory",
        "documentNamespace": f"https://clipforge.local/spdx/{created.replace(':', '-')}",
        "creationInfo": {
            "creators": ["Tool: scripts/generate_macos_sbom.py"],
            "created": created,
            "comment": "Python package versions are read from the clean Python 3.11 build environment; production npm packages are read from the lockfile. Bundled binary hashes are recorded when staged. License fields are metadata hints and require release review.",
        },
        "packages": sbom_packages,
        "relationships": [{
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": "SPDXRef-ClipForge-Application",
        }],
        "annotations": [{
            "annotationDate": created,
            "annotationType": "OTHER",
            "annotator": "Tool: scripts/generate_macos_sbom.py",
            "comment": f"Target: macOS arm64; Python {platform.python_version()}; Node packages from ui/package-lock.json. This is an environment inventory and must be reviewed against the final packaged tree before release.",
        }],
    }
    document["packages"].insert(0, {
        "SPDXID": "SPDXRef-ClipForge-Application",
        "name": "ClipForge",
        "versionInfo": json.loads((ROOT / "ui" / "package.json").read_text(encoding="utf-8"))["version"],
        "downloadLocation": "NOASSERTION",
        "filesAnalyzed": False,
        "licenseConcluded": "NOASSERTION",
        "licenseDeclared": "AGPL-3.0-or-later",
        "copyrightText": "NOASSERTION",
        "primaryPackagePurpose": "APPLICATION",
    })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} ({len(sbom_packages)} dependencies/binaries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
