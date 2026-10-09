"""Verify VERSION and every distribution's pyproject version agree.

The release pipeline reads VERSION for the GitHub tag/artifact names while
uv/twine read the per-project versions; a mismatch ships wheels whose
versions differ from the tag. Run via `make check-versions`.
"""

import pathlib
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PYPROJECTS = [
    ROOT / "pyproject.toml",
    ROOT / "client" / "pd-cds-api" / "pyproject.toml",
    ROOT / "client" / "pd-cds-api-bin" / "pyproject.toml",
    ROOT / "client" / "pd-cds-cli" / "pyproject.toml",
]


def main() -> int:
    """Compare VERSION against every distribution's pyproject version.

    Returns:
        0 when all versions agree, 1 when drift is detected (offending
        files are printed to stderr).
    """
    version = (ROOT / "VERSION").read_text().strip()
    mismatches = []
    for path in PYPROJECTS:
        got = tomllib.loads(path.read_text())["project"]["version"]
        if got != version:
            rel = path.relative_to(ROOT)
            mismatches.append(f"  {rel}: {got} != VERSION {version}")
    if mismatches:
        print(f"version drift detected (VERSION = {version}):", file=sys.stderr)
        print("\n".join(mismatches), file=sys.stderr)
        return 1
    print(f"all versions consistent at {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
