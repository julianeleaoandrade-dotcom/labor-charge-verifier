"""Assemble the static site for GitHub Pages into a folder (default: _site).

The page in web/ runs the Python package in the browser with Pyodide, so the
site needs the package source, the example settings, the sample data and the
blank templates next to the page. Nothing here is generated or changed; the
files are copied as they are in the repository.

Usage: python scripts/build_site.py [output_folder]
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Pure-Python wheels served next to the page so the browser can read .xlsx
# files. Pinned for reproducible builds.
WHEELS = ["openpyxl==3.1.5", "et-xmlfile==2.0.0"]


def download_wheels(folder: Path) -> list[str]:
    folder.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "pip", "download", "--quiet", "--no-deps",
                    "--only-binary=:all:", "--dest", str(folder), *WHEELS], check=True)
    names = sorted(p.name for p in folder.glob("*.whl"))
    if len(names) != len(WHEELS):
        raise SystemExit(f"Expected {len(WHEELS)} wheels, found {names}")
    (folder / "manifest.json").write_text(json.dumps(names))
    return names


def build(out: Path, wheels: bool = True) -> None:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "web", out)
    package = out / "py" / "labor_charge_verifier"
    package.mkdir(parents=True)
    for source in sorted((ROOT / "src" / "labor_charge_verifier").glob("*.py")):
        shutil.copy2(source, package / source.name)
    (out / "config").mkdir()
    shutil.copy2(ROOT / "config" / "settings.example.yaml", out / "config")
    shutil.copytree(ROOT / "sample-data", out / "sample-data")
    shutil.copytree(ROOT / "templates", out / "templates")
    if wheels:
        download_wheels(out / "wheels")
    else:
        (out / "wheels").mkdir()
        (out / "wheels" / "manifest.json").write_text("[]")
    (out / ".nojekyll").write_text("")
    print(f"Site written to {out}")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "_site")
