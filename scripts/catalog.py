#!/usr/bin/env python3
"""Extract bundled CSS literals and index declared theme variables without execution."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEETS = (
    "base", "corner_shape", "design_platform", "focus", "onboarding",
    "scrollbar", "gradient_shadow_text", "shiki",
)


def baseline():
    pointer = json.loads((ROOT / "logs/latest-baseline.json").read_text())
    manifest_path = ROOT / pointer["manifest"]
    manifest = json.loads(manifest_path.read_text())
    if manifest["asar_sha256"] != pointer["asar_sha256"]:
        raise ValueError("Baseline pointer does not match manifest")
    return manifest_path.parent, manifest


def main():
    snapshot, manifest = baseline()
    source = snapshot / "packages/dsh-client-ui-theme/lib/client.js"
    text = source.read_text()
    output = snapshot / "derived"
    (output / "theme-css").mkdir(parents=True, exist_ok=True)
    tokens = {}
    for name in SHEETS:
        match = re.search(r'\bvar ' + name + r'_css_default = ("(?:\\.|[^"\\])*");', text)
        if not match:
            raise ValueError(f"Bundled stylesheet shape changed: {name}")
        css = json.loads(match.group(1))
        filename = name.replace("_", "-") + ".css"
        (output / "theme-css" / filename).write_text(css + "\n")
        for rule in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
            selector, declarations = rule.groups()
            for declaration in re.finditer(r'(--[a-zA-Z][\w-]*)\s*:\s*([^;{}]+)', declarations):
                token, value = declaration.groups()
                tokens.setdefault(token, {"declarations": [], "used_by": []})["declarations"].append({
                    "sheet": filename, "selector": selector.strip(), "value": value.strip(),
                    "bundle_line": text.count("\n", 0, match.start()) + 1,
                })
    for source in sorted((snapshot / "packages").glob("*/lib/client.js")):
        used = set(re.findall(r'var\(\s*(--[a-zA-Z][\w-]*)', source.read_text()))
        for token in used & tokens.keys():
            tokens[token]["used_by"].append(source.parts[-3])
    catalog = {
        "schema_version": 1, "app_version": manifest["version"],
        "asar_sha256": manifest["asar_sha256"], "stylesheet_count": len(SHEETS),
        "token_count": len(tokens),
        "scope": "Literal declarations in 8 bundled theme sheets; not computed styles. Selector text is the innermost rule; conditional ancestors are not flattened. Usage is a textual search of selected client bundles only.",
        "tokens": dict(sorted(tokens.items())),
    }
    (output / "token-catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"stylesheets": len(SHEETS), "tokens": len(tokens),
                      "catalog": str(output / "token-catalog.json")}, indent=2))


if __name__ == "__main__":
    main()
