#!/usr/bin/env python3
"""Read the installed Harness ASAR and preserve a verified UI reference snapshot."""
import argparse
import hashlib
import json
import plistlib
import re
import struct
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = (
    "dsh-client-ui-theme", "dsh-client-ui-layout", "dsh-client-ui-sidebar",
    "dsh-client-ui-conversation", "dsh-client-ui-chat", "dsh-client-ui-settings",
    "dsh-client-ui-settings-general", "dsh-client-ui-entry-customization",
    "dsh-client-modules", "dsh-plugin-manager", "dsh-host-plugin-inventory",
    "dsh-client-ui-plugin-manager", "dsh-harness-dev-context",
    "dsh-package-manifest", "dsh-cordis-client-runner",
    "dsh-experimental-terminal-bundle",
)
PACKAGE_PREFIX = "dsh/node_modules/@deepseek-ai/"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Asar:
    """Read regular ASAR members only; never execute or follow archive links."""

    def __init__(self, path):
        self.path = path
        self.size = path.stat().st_size
        with path.open("rb") as stream:
            prefix = stream.read(16)
            if len(prefix) != 16:
                raise ValueError("Truncated ASAR header")
            size_size, header_size, payload_size, text_size = struct.unpack("<4I", prefix)
            if (size_size != 4 or header_size != payload_size + 4
                    or text_size > payload_size - 4 or header_size > self.size - 8):
                raise ValueError("Invalid ASAR header bounds")
            raw_header = stream.read(text_size)
        self.header_sha256 = sha256(raw_header)
        self.data_offset = 8 + header_size
        self.entries = {}
        self._walk(json.loads(raw_header), PurePosixPath())

    def _walk(self, directory, parent):
        for name, entry in directory.get("files", {}).items():
            if name in (".", "..") or "/" in name or "\\" in name:
                raise ValueError(f"Unsafe archive member: {name!r}")
            member = parent / name
            if "files" in entry:
                self._walk(entry, member)
            else:
                self.entries[str(member)] = entry

    def read(self, member):
        entry = self.entries[member]
        if "link" in entry:
            raise ValueError(f"Archive links are not extracted: {member}")
        size = entry["size"]
        if entry.get("unpacked"):
            unpacked = Path(str(self.path) + ".unpacked").resolve()
            source = (unpacked / member).resolve()
            if not source.is_relative_to(unpacked):
                raise ValueError(f"Unpacked path escapes its root: {member}")
            data = source.read_bytes()
        else:
            start = self.data_offset + int(entry["offset"])
            if start < self.data_offset or size < 0 or start + size > self.size:
                raise ValueError(f"Invalid archive member bounds: {member}")
            with self.path.open("rb") as stream:
                stream.seek(start)
                data = stream.read(size)
        if len(data) != size:
            raise ValueError(f"Truncated member: {member}")
        integrity = entry.get("integrity", {})
        if integrity:
            if integrity.get("algorithm") != "SHA256":
                raise ValueError(f"Unsupported member integrity: {member}")
            if sha256(data) != integrity["hash"]:
                raise ValueError(f"Member hash mismatch: {member}")
        return data


def selected_destination(member):
    if member in ("package.json", "lib/main.js", "lib/preload-app.cjs",
                  "renderer/assets/window-material.css"):
        return Path("desktop") / member
    for package in PACKAGES:
        prefix = PACKAGE_PREFIX + package + "/"
        if member.startswith(prefix):
            return Path("packages") / package / member[len(prefix):]
    frontend = PACKAGE_PREFIX + "dsh-web-frontend/"
    if member.startswith(frontend) and (
        member.endswith((".css", ".html"))
        or member == frontend + "package.json"
        or member == frontend + "LICENSE"
    ):
        return Path("packages/dsh-web-frontend") / member[len(frontend):]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=Path("/Applications/DeepSeek Harness.app"))
    args = parser.parse_args()
    contents = args.app.resolve() / "Contents"
    plist_path = contents / "Info.plist"
    info = plistlib.loads(plist_path.read_bytes())
    archive = Asar(contents / "Resources/app.asar")
    declared = info.get("ElectronAsarIntegrity", {}).get("Resources/app.asar", {})
    if declared and (declared.get("algorithm") != "SHA256"
                     or declared.get("hash") != archive.header_sha256):
        raise ValueError("Info.plist ASAR header integrity mismatch")
    digest = file_hash(archive.path)
    version = info["CFBundleShortVersionString"]
    safe_version = re.sub(r"[^a-zA-Z0-9._-]", "_", version)
    destination = ROOT / "reference" / f"{safe_version}-{digest[:12]}"
    selected = []
    for member in sorted(archive.entries):
        relative = selected_destination(member)
        if relative is None:
            continue
        data = archive.read(member)
        target = destination / relative
        if target.exists():
            if target.read_bytes() != data:
                raise ValueError(f"Reference changed locally; refusing to overwrite: {target}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        selected.append({"archive_path": member, "snapshot_path": str(relative),
                         "size": len(data), "sha256": sha256(data),
                         "member_integrity_verified": bool(archive.entries[member].get("integrity"))})
    if file_hash(archive.path) != digest or plistlib.loads(plist_path.read_bytes()) != info:
        raise ValueError("Application changed during capture; snapshot not accepted")
    manifest = {
        "schema_version": 1, "captured_at": datetime.now(timezone.utc).isoformat(),
        "app_path": str(args.app.resolve()), "bundle_id": info["CFBundleIdentifier"],
        "version": version, "asar_sha256": digest,
        "asar_header_sha256": archive.header_sha256,
        "plist_header_integrity_verified": bool(declared),
        "archive_member_count": len(archive.entries),
        "selected_file_count": len(selected), "files": selected,
        "scope": "Packaged UI reference only; no user data, target execution or installed-app writes.",
    }
    manifest_path = destination / "manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        if previous["asar_sha256"] != digest:
            raise ValueError("Existing manifest has a different application identity")
        manifest["captured_at"] = previous["captured_at"]
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if not manifest_path.exists() or manifest_path.read_text() != manifest_text:
        manifest_path.write_text(manifest_text)
    (ROOT / "logs").mkdir(exist_ok=True)
    (ROOT / "logs/latest-baseline.json").write_text(json.dumps({
        "manifest": str(manifest_path.relative_to(ROOT)), "asar_sha256": digest
    }, indent=2) + "\n")
    print(json.dumps({"version": version, "snapshot": str(destination),
                      "selected_files": len(selected), "asar_sha256": digest}, indent=2))


if __name__ == "__main__":
    main()
