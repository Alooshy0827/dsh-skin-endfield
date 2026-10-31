#!/usr/bin/env python3
"""Keep README compatibility tied to the current verified skin release."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- dsh-compatibility:start -->"
END = "<!-- dsh-compatibility:end -->"


def render_readme(text, report):
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("README must contain exactly one DSH compatibility block")
    skin = report["version"]
    dsh = report["dsh_version"]
    block = (
        f"{START}\n"
        f"**最新实测适配的 DSH 版本：`{dsh}`**\n\n"
        f"当前皮肤版本：**v{skin}**。已通过桌面与隔离实例验证。\n\n"
        f"[下载插件 ZIP](releases/dsh-skin-local-{skin}.zip) · "
        f"[发布校验记录](releases/dsh-skin-local-{skin}.verification.json)\n"
        f"{END}"
    )
    result, count = re.subn(re.escape(START) + r".*?" + re.escape(END),
                            lambda _: block, text, flags=re.S)
    if count != 1:
        raise ValueError("README compatibility block markers are out of order")
    return result


def verified_release(root=ROOT):
    package = json.loads((root / "skin/package.json").read_text())
    version = package["version"]
    release = root / "releases" / f"dsh-skin-local-{version}"
    report = json.loads(release.with_name(release.name + ".verification.json").read_text())
    if (report["status"] != "verified" or report["version"] != version
            or report["dsh_version"] != package["engines"]["dsh"]):
        raise ValueError("Current skin and tested DSH version must match a verified release")
    for relative, digest in report["files"].items():
        if hashlib.sha256((release / relative).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Verified release file changed: {relative}")
    frozen = json.loads((release / "package.json").read_text())
    if frozen != package:
        raise ValueError("Source package metadata differs from the verified release")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Update from the verified release")
    mode.add_argument("--check", action="store_true", help="Fail if README is stale (default)")
    args = parser.parse_args()
    report = verified_release()
    readme = ROOT / "README.md"
    original = readme.read_text()
    expected = render_readme(original, report)
    if args.write:
        readme.write_text(expected)
    elif original != expected:
        raise ValueError("README compatibility is stale; run scripts/compatibility.py --write")
    print(json.dumps({"status": "passed", "skin_version": report["version"],
                      "latest_tested_dsh": report["dsh_version"]}, indent=2))


if __name__ == "__main__":
    main()
