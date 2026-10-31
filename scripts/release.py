#!/usr/bin/env python3
"""Freeze a runtime-tested candidate; finalize only after desktop verification.

No installation or external profile writes. Run for every skin version.
"""
import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from build import DESTINATION, ROOT
from compatibility import render_readme
from prepare import file_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="store_true", help="Freeze the exact build for desktop testing")
    args = parser.parse_args()
    subprocess.run([sys.executable, str(ROOT / "scripts/check.py")], check=True)
    build = json.loads((ROOT / "dist/build-report.json").read_text())
    qa = ROOT / "qa" / f"v{build['version']}"
    runtime = json.loads((qa / "runtime.json").read_text())
    if runtime["version"] != build["version"] or runtime["dshVersion"] != build["reference_version"]:
        raise ValueError("Runtime evidence targets a different skin or DSH version")
    if runtime["builtFiles"] != build["files"]:
        raise ValueError("Runtime evidence is stale: test this exact build before releasing")
    for page in ("home", "pluginPage", "settings"):
        if runtime[page]["differences"] or runtime[page]["controls"] < 20:
            raise ValueError(f"Geometry regression or incomplete evidence: {page}")
    if runtime["rollback"] != {"bodyToken": "", "intro": 0, "skin": None, "styles": 0}:
        raise ValueError("Rollback did not restore original appearance")
    if runtime["coldStartLogs"] or runtime["coldStart"] != {"editor": True, "overlay": 0, "skin": build["version"], "styles": 1}:
        raise ValueError("Cold-start verification failed")
    if not all(runtime["checks"].values()):
        raise ValueError("Complete the runtime checklist")
    stylesheet = runtime["stylesheet"]
    if not stylesheet["actual"] or stylesheet["actual"] != stylesheet["expected"]:
        raise ValueError("Runtime stylesheet does not match the tested build")
    target = ROOT / "releases" / f"dsh-skin-local-{build['version']}"
    if target.exists():
        for rel, digest in build["files"].items():
            if not (target / rel).is_file() or file_hash(target / rel) != digest:
                raise ValueError("A frozen version must never be overwritten. Bump the version and retest.")
    else:
        shutil.copytree(DESTINATION, target)
    status = "candidate"
    updated_readme = None
    if not args.candidate:
        desktop = json.loads((qa / "desktop.json").read_text())
        if desktop["version"] != build["version"] or desktop["dshVersion"] != build["reference_version"]:
            raise ValueError("Desktop evidence targets a different skin or DSH version")
        if desktop["builtFiles"] != build["files"] or not all(desktop["checks"].values()):
            raise ValueError("Desktop evidence missing, stale or failed")
        if desktop["status"] != "passed":
            raise ValueError("Desktop verification did not pass")
        updated_readme = render_readme((ROOT / "README.md").read_text(), {
            "version": build["version"], "dsh_version": build["reference_version"]
        })
        status = "verified"
        with zipfile.ZipFile(target.parent / f"{target.name}.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for rel in build["files"]:
                archive.write(target / rel, f"{target.name}/{rel}")
    report = {"status": status, "version": build["version"], "dsh_version": build["reference_version"],
              "asar_sha256": build["asar_sha256"], "files": build["files"],
              "verified_at": datetime.now(timezone.utc).isoformat(), "evidence": str(qa)}
    (target.parent / f"{target.name}.verification.json").write_text(json.dumps(report, indent=2) + "\n")
    if updated_readme is not None:
        (ROOT / "README.md").write_text(updated_readme)
    print(json.dumps({"status": status, "package": str(target)}, indent=2))


if __name__ == "__main__":
    main()
