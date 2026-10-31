#!/usr/bin/env python3
"""Check baseline identity, snapshot files, skin inputs and built JS syntax."""
import json
import re
import shutil
import subprocess
from pathlib import Path

from build import DESTINATION, inputs, rendered_client
from catalog import baseline
from prepare import file_hash

ROOT = Path(__file__).resolve().parents[1]


def check_css_geometry():
    """Check every host rule, including rules after fonts and inside media queries."""
    appearance = {"background", "background-color", "background-image", "background-position",
                  "background-size", "background-repeat", "color", "border-color", "border-radius",
                  "box-shadow", "clip-path", "text-decoration-color", "text-underline-offset",
                  "transition", "transition-duration", "animation", "outline", "outline-offset"}
    decoration = appearance | {"content", "position", "inset", "width", "height", "pointer-events",
                               "mask-image", "mask-size", "mask-repeat", "opacity"}
    for filename in ("appearance.css", "details.css"):
        css = (ROOT / "skin" / filename).read_text()
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        for selector, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            selector = selector.strip()
            if selector.startswith("@font-face") or selector.startswith(".dsh-ef-"):
                continue
            props = re.findall(r"(?:^|;)\s*([\w-]+)\s*:\s*([^;]+)", declarations)
            if re.fullmatch(r"(?:from|to|\d+%)", selector):
                if any(p not in {"opacity", "transform", "clip-path", "background-size", "visibility"} for p, _ in props):
                    raise ValueError(f"Animation changes geometry: {filename}: {selector}")
                continue
            if not selector.startswith("body[data-dsh-endfield-skin]"):
                raise ValueError(f"Unscoped appearance selector: {filename}: {selector}")
            pseudo = selector.endswith(("::before", "::after"))
            for prop, value in props:
                if prop.startswith("--dsh-ef-"):
                    continue
                if prop not in (decoration if pseudo else appearance):
                    raise ValueError(f"Host geometry/behavior property requires review: {filename}: {prop}")
                if pseudo and prop in {"content", "position", "pointer-events"}:
                    if value.strip() != {"content": '\"\"', "position": "absolute", "pointer-events": "none"}[prop]:
                        raise ValueError(f"Decoration must stay empty and non-interactive: {selector}")


def main():
    snapshot, manifest = baseline()
    archive = Path(manifest["app_path"]) / "Contents/Resources/app.asar"
    if file_hash(archive) != manifest["asar_sha256"]:
        raise ValueError("Installed Harness changed. Run prepare.py, catalog.py, then review compatibility.")
    for row in manifest["files"]:
        if file_hash(snapshot / row["snapshot_path"]) != row["sha256"]:
            raise ValueError(f"Reference file changed: {row['snapshot_path']}")
    _, package, tokens, template = inputs()
    # Enforce the user's geometry constraint on each build, not only this version.
    for name in tokens:
        if not name.startswith(("--dsw-alias-", "--dsw-specific-", "--dsw-radius-", "--dsw-shadow-")) and name not in {"--dsw-corner-shape", "--ds-ease-in-out"}:
            raise ValueError(f"Non-appearance token requires review: {name}")
        if any(x in name for x in ("state-error", "state-success", "state-warn", "code-diff", "file-diff")):
            raise ValueError(f"Semantic status token must stay native: {name}")
    check_css_geometry()
    if re.search(r"\b(fetch|XMLHttpRequest|WebSocket|localStorage|sessionStorage|eval)\s*[.(]", template):
        raise ValueError("Skin must remain local and must not access application data")
    report = json.loads((ROOT / "dist/build-report.json").read_text())
    if report["asar_sha256"] != manifest["asar_sha256"]:
        raise ValueError("Build belongs to a different baseline")
    if json.loads((DESTINATION / "package.json").read_text()) != package:
        raise ValueError("Package metadata changed; rebuild")
    if (DESTINATION / "lib/client.js").read_text() != rendered_client(template, tokens):
        raise ValueError("Token inputs or client template changed; rebuild")
    for relative, source in [("lib/index.js", "skin/host.js"),
                             ("cordis.patch.yml", "skin/cordis.patch.yml")]:
        if (DESTINATION / relative).read_bytes() != (ROOT / source).read_bytes():
            raise ValueError(f"Build input changed: {source}; rebuild")
    for relative, digest in report["files"].items():
        if file_hash(DESTINATION / relative) != digest:
            raise ValueError(f"Built file changed: {relative}")
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is needed for JS syntax checks; no dependencies need installing")
    for relative in ("lib/index.js", "lib/client.js"):
        subprocess.run([node, "--check", str(DESTINATION / relative)], check=True)
    subprocess.run([node, "--test", str(ROOT / "scripts/test-skin.mjs")], check=True)
    result = {"status": "passed", "app_version": manifest["version"],
              "reference_files_verified": len(manifest["files"]),
              "theme_overrides": len(tokens), "javascript_syntax": "passed",
              "lifecycle_and_fault_tests": "passed (8 tests, including 100 cycles)",
              "host_geometry_property_guard": "passed",
              "runtime_integration": "not run", "installed_app_modified": False}
    (ROOT / "logs/check-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
