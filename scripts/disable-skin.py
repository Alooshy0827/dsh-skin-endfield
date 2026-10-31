#!/usr/bin/env python3
"""Emergency appearance rollback, independent of DSH startup.

Only deselects dsh-skin-local from a profile. Keeps all other plugins and settings.
Close DSH before running, then reopen. An exact manifest backup is retained.
"""
import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def disable(profile: Path):
    manifest = profile / "package.json"
    raw = manifest.read_bytes()
    data = json.loads(raw)
    bundles = data["dsh"]["profile"]["bundles"]
    if not isinstance(bundles, list):
        raise ValueError("Unrecognized profile bundle list; no change made")
    if "dsh-skin-local" not in bundles:
        return {"changed": False, "profile": str(profile)}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = profile / f"package.json.before-skin-disable-{stamp}"
    backup.write_bytes(raw)
    data["dsh"]["profile"]["bundles"] = [b for b in bundles if b != "dsh-skin-local"]
    fd, tmp = tempfile.mkstemp(prefix=".skin-rollback-", dir=profile)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        os.chmod(tmp, manifest.stat().st_mode & 0o777)
        os.replace(tmp, manifest)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return {"changed": True, "profile": str(profile), "backup": str(backup), "next": "Reopen DSH"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-dir", type=Path, default=Path.home() / ".dsh/profiles/desktop")
    args = parser.parse_args()
    print(json.dumps(disable(args.profile_dir), ensure_ascii=False, indent=2))
