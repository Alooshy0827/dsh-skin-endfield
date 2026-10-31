#!/usr/bin/env python3
"""Build a local Harness skin package; does not install or activate it."""
import base64
import json
from pathlib import Path

from catalog import baseline
from prepare import file_hash

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "dist/dsh-skin-local"
MARKER = "/* TOKEN_OVERRIDES */ {}"
CSS_MARKER = '/* SKIN_CSS */ ""'


def rendered_client(template, tokens):
    css = (ROOT / "skin/appearance.css").read_text() + "\n" + (ROOT / "skin/details.css").read_text()
    for marker, filename, mime in [
        ("__SAIRA_DATA_URL__", "Saira.ttf", "font/ttf"),
        ("__NOISE_DATA_URL__", "noise.png", "image/png"),
        ("__TWILL_DATA_URL__", "twill.png", "image/png"),
        ("__CONTOURS_DATA_URL__", "contours.png", "image/png"),
        ("__WORDMARK_DATA_URL__", "harness-wordmark.svg", "image/svg+xml"),
    ]:
        if css.count(marker) != 1:
            raise ValueError(f"Expected one asset marker: {marker}")
        data = base64.b64encode((ROOT / "skin/assets" / filename).read_bytes()).decode()
        css = css.replace(marker, f"data:{mime};base64,{data}")
    if template.count(CSS_MARKER) != 1:
        raise ValueError("Expected one CSS marker")
    return template.replace(MARKER, json.dumps(tokens, ensure_ascii=False, indent=2)).replace(
        CSS_MARKER, json.dumps(css, ensure_ascii=False))


def inputs():
    snapshot, manifest = baseline()
    catalog = json.loads((snapshot / "derived/token-catalog.json").read_text())
    if catalog["asar_sha256"] != manifest["asar_sha256"]:
        raise ValueError("Token catalog belongs to a different baseline")
    package = json.loads((ROOT / "skin/package.json").read_text())
    if package["engines"]["dsh"] != manifest["version"]:
        raise ValueError("New Harness version: review the plugin contract before updating engines.dsh")
    tokens = json.loads((ROOT / "skin/tokens.json").read_text())
    if not isinstance(tokens, dict):
        raise ValueError("tokens.json must be an object")
    for name, modes in tokens.items():
        if name not in catalog["tokens"]:
            raise ValueError(f"Unknown baseline token: {name}")
        if not isinstance(modes, dict) or set(modes) != {"light", "dark"}:
            raise ValueError(f"{name}: supply both light and dark values")
        if any(not isinstance(value, str) or not value.strip() for value in modes.values()):
            raise ValueError(f"{name}: values must be non-empty CSS strings")
    template = (ROOT / "skin/client.template.js").read_text()
    if template.count(MARKER) != 1:
        raise ValueError("Client template must contain exactly one token marker")
    return manifest, package, tokens, template


def main():
    manifest, package, tokens, template = inputs()
    DESTINATION.joinpath("lib").mkdir(parents=True, exist_ok=True)
    DESTINATION.joinpath("lib/client.js").write_text(rendered_client(template, tokens))
    DESTINATION.joinpath("lib/index.js").write_text((ROOT / "skin/host.js").read_text())
    DESTINATION.joinpath("package.json").write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n")
    DESTINATION.joinpath("cordis.patch.yml").write_text((ROOT / "skin/cordis.patch.yml").read_text())
    DESTINATION.joinpath("LICENSES").mkdir(exist_ok=True)
    DESTINATION.joinpath("LICENSES/Saira-OFL.txt").write_bytes((ROOT / "skin/assets/Saira-OFL.txt").read_bytes())
    DESTINATION.joinpath("ASSETS.json").write_bytes((ROOT / "skin/assets/manifest.json").read_bytes())
    paths = ["package.json", "cordis.patch.yml", "lib/index.js", "lib/client.js", "LICENSES/Saira-OFL.txt", "ASSETS.json"]
    report = {
        "reference_version": manifest["version"], "asar_sha256": manifest["asar_sha256"],
        "version": package["version"],
        "token_count": len(tokens), "style_status": "Endfield",
        "installed": False, "runtime_verified": False,
        "files": {path: file_hash(DESTINATION / path) for path in paths},
    }
    (ROOT / "dist/build-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"package": str(DESTINATION), "token_overrides": len(tokens),
                      "installed": False}, indent=2))


if __name__ == "__main__":
    main()
