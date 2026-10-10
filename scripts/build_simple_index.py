"""Generate the PEP 503 "simple" repository index for the pd-cds wheels.

Institutional constraints block PyPI publishing, so the built wheels and
sdists ship as GitHub Release assets referenced from a static index that
``pages.yml`` deploys to the project's GitHub Pages site under
``/simple/``. Two modes:

``--from-releases`` (production; every Pages deploy)
    Enumerate the repository's GitHub Releases through the REST API and
    rewrite the whole tree statelessly. Integrity digests come from each
    asset's ``digest`` field when the API provides one, otherwise the
    asset is downloaded and hashed.

``--wheels DIR --tag TAG`` (incremental, local dev)
    Merge unpacked artifacts from a local directory into an existing (or
    empty) tree, computing sha256 digests from the local files.

Only stdlib is used so the script runs anywhere python3 does, respecting
the official-actions-only CI constraint. Unit tests (incl. golden HTML)
live under ``scripts/tests/``.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import pathlib
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

DEFAULT_PROJECTS = ("pd-cds-api", "pd-cds-api-bin", "pd-cds-cli")
API_VERSION = "2022-11-28"
USER_AGENT = "pd-cds-build-simple-index"
PAGE_SIZE = 100
MAX_PAGES = 200  # safety stop: 20k releases is far beyond this project

_NAME_SEPARATORS = re.compile(r"[-_.]+")
_VERSION_SEPARATORS = re.compile(r"[.\-+_]+")
_ANCHOR_RE = re.compile(r'<a href="([^"]+)">([^<]*)</a>')
_VERSION_START = re.compile(r"^\d")


def normalize(name: str) -> str:
    """Return the PEP 503 normalized form of a project name.

    Args:
        name: Raw project name (underscores, dots, dashes, any case).

    Returns:
        Lowercased name with runs of ``-_. `` collapsed to single dashes.
    """
    return _NAME_SEPARATORS.sub("-", name).lower()


def classify_artifact(filename: str, projects: Iterable[str]) -> str | None:
    """Map a release asset filename to its whitelisted distribution.

    Args:
        filename: Asset name, e.g. ``pd_cds_cli-0.2.0-py3-none-any.whl``.
        projects: Allowed distribution names (matched normalized).

    Returns:
        The normalized project name, or None when the file is not a
        whitelisted wheel/sdist artifact (zip bundles, other names).
    """
    allowed = {normalize(p) for p in projects}
    raw: str | None = None
    if filename.endswith(".whl"):
        stem = filename.removesuffix(".whl").split("-")
        if len(stem) >= 5:
            raw = stem[0]
    elif filename.endswith(".tar.gz"):
        head, sep, version = filename.removesuffix(".tar.gz").rpartition("-")
        if sep and _VERSION_START.match(version):
            raw = head
    if raw is None:
        return None
    normalized = normalize(raw)
    return normalized if normalized in allowed else None


def artifact_version(filename: str) -> tuple[Any, ...]:
    """Extract a sort key approximating the artifact's distribution version.

    Not a full PEP 440 parser — release versions here are plain semver and
    the key only needs to be deterministic and newest-first.

    Args:
        filename: Wheel or sdist filename.

    Returns:
        Tuple ordering numeric parts before string parts, higher first
        after inversion by the caller.
    """
    if filename.endswith(".whl"):
        version = filename.removesuffix(".whl").split("-")[1]
    else:
        version = filename.removesuffix(".tar.gz").rpartition("-")[2]
    parts: list[Any] = []
    for part in _VERSION_SEPARATORS.split(version):
        parts.append((0, int(part), "") if part.isdigit() else (1, 0, part))
    return tuple(parts)


@dataclass(frozen=True)
class Artifact:
    """One wheel/sdist file as referenced by a project index page."""

    filename: str
    url: str
    sha256: str | None

    @property
    def href(self) -> str:
        """Return the PEP 503 anchor href with integrity fragment."""
        return self.url + (f"#sha256={self.sha256}" if self.sha256 else "")

    @property
    def base_url(self) -> str:
        """Return the artifact URL without any integrity fragment."""
        return self.url.split("#", 1)[0]

    @property
    def version_key(self) -> tuple[Any, ...]:
        """Return the ordering key for this artifact's file name."""
        return artifact_version(self.filename)


def render_root_page(projects: Iterable[str]) -> str:
    """Render the top-level simple index listing project directories.

    Args:
        projects: Normalized project names to link (sorted for output).

    Returns:
        Complete HTML document bytes-as-text.
    """
    anchors = "\n".join(
        f'<a href="{html.escape(p)}/">{html.escape(p)}</a>' for p in sorted(projects)
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        "<title>Simple index</title>\n"
        "</head>\n"
        "<body>\n"
        "<h1>Simple index</h1>\n"
        f"{anchors}\n"
        "</body>\n"
        "</html>\n"
    )


def render_project_page(project: str, artifacts: Iterable[Artifact]) -> str:
    """Render a PEP 503 project page, newest version first.

    Args:
        project: Normalized project name used in the heading.
        artifacts: Files to list (deduplicated by caller, ordered here).

    Returns:
        Complete HTML document bytes-as-text.
    """
    ordered = sorted(artifacts, key=lambda a: (a.version_key, a.filename), reverse=True)
    anchors = "\n".join(
        f'<a href="{html.escape(a.href, quote=True)}">{html.escape(a.filename)}</a>'
        for a in ordered
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>Links for {html.escape(project)}</title>\n"
        "</head>\n"
        "<body>\n"
        f"<h1>Links for {html.escape(project)}</h1>\n"
        f"{anchors}\n"
        "</body>\n"
        "</html>\n"
    )


def _entries_to_artifacts(entries: dict[str, tuple[str, str | None]]) -> list[Artifact]:
    """Convert parsed ``base_url -> (filename, sha256)`` maps to Artifacts.

    Args:
        entries: Merged entry mapping (deduplication happens via the key).

    Returns:
        Artifact list in insertion order.
    """
    return [Artifact(filename=f, url=url, sha256=sha) for url, (f, sha) in entries.items()]


def parse_project_page(text: str) -> dict[str, tuple[str, str | None]]:
    """Parse an existing project page into mergeable entries.

    Args:
        text: HTML of a previously generated ``index.html``.

    Returns:
        Mapping of base URL to (filename, sha256-or-None) per anchor.
    """
    entries: dict[str, tuple[str, str | None]] = {}
    for href, filename in _ANCHOR_RE.findall(text):
        url, _, fragment = href.partition("#")
        sha = fragment.removeprefix("sha256=") if fragment.startswith("sha256=") else None
        entries[url] = (html.unescape(filename), sha)
    return entries


def parse_root_page(text: str) -> list[str]:
    """Parse an existing root page into its project directory names.

    Args:
        text: HTML of a previously generated root ``index.html``.

    Returns:
        Sorted list of project names linked from the page.
    """
    return sorted(
        html.unescape(href).rstrip("/") for href, _ in _ANCHOR_RE.findall(text)
    )


def load_existing_tree(out: pathlib.Path) -> dict[str, dict[str, tuple[str, str | None]]]:
    """Read an existing generated tree so incremental mode can merge.

    Args:
        out: Output directory (``site/simple``-style) that may or may not
            already contain a previous tree.

    Returns:
        Mapping of project name to its parsed entry mapping.
    """
    root = out / "index.html"
    if not root.is_file():
        return {}
    pages: dict[str, dict[str, tuple[str, str | None]]] = {}
    for project in parse_root_page(root.read_text(encoding="utf-8")):
        page = out / project / "index.html"
        pages[project] = (
            parse_project_page(page.read_text(encoding="utf-8")) if page.is_file() else {}
        )
    return pages


def write_tree(out: pathlib.Path, pages: dict[str, dict[str, tuple[str, str | None]]]) -> None:
    """Write the complete index tree (root page + one page per project).

    Args:
        out: Destination directory; created if missing.
        pages: Mapping of project name to ``base_url -> (filename, sha)``.
    """
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(render_root_page(pages), encoding="utf-8")
    for project, entries in pages.items():
        project_dir = out / project
        project_dir.mkdir(exist_ok=True)
        (project_dir / "index.html").write_text(
            render_project_page(project, _entries_to_artifacts(entries)), encoding="utf-8"
        )


def sha256_of_file(path: pathlib.Path, chunk: int = 1 << 20) -> str:
    """Hash a local artifact file.

    Args:
        path: File to read.
        chunk: Read buffer size in bytes.

    Returns:
        Lowercase hex sha256 digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest()


Opener = Callable[[urllib.request.Request], Any]


def build_request(url: str, token: str | None) -> urllib.request.Request:
    """Construct a GitHub-API-friendly request with auth headers.

    Args:
        url: API URL to fetch.
        token: Optional bearer token (``GITHUB_TOKEN``).

    Returns:
        Prepared, fetchable request object.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def sha256_of_url(url: str, *, token: str | None, opener: Opener, chunk: int = 1 << 20) -> str:
    """Download an asset and hash it (fallback when the API lacks digests).

    Args:
        url: Direct asset download URL.
        token: Optional bearer token.
        opener: Injectable urlopen-compatible callable.
        chunk: Stream buffer size in bytes.

    Returns:
        Lowercase hex sha256 digest of the asset bytes.
    """
    digest = hashlib.sha256()
    with opener(build_request(url, token)) as response:
        while block := response.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def load_releases(
    repo: str, *, token: str | None, api_base: str, opener: Opener
) -> list[dict[str, Any]]:
    """Fetch every release of a repository through the GitHub REST API.

    Args:
        repo: ``owner/name`` slug.
        token: Optional bearer token for the API calls.
        api_base: REST API base, e.g. ``https://api.github.com``.
        opener: Injectable urlopen-compatible callable.

    Returns:
        Raw release objects (paginated, ascending pages preserved).

    Raises:
        SystemExit: On HTTP errors or pagination runaway.
    """
    releases: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        url = f"{api_base}/repos/{repo}/releases?per_page={PAGE_SIZE}&page={page}"
        try:
            with opener(build_request(url, token)) as response:
                batch = json.load(response)
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            sys.exit(f"error: release enumeration failed for {url}: {exc}")
        releases.extend(batch)
        if len(batch) < PAGE_SIZE:
            return releases
    sys.exit(f"error: exceeded {MAX_PAGES} release pages for {repo}; aborting")


def artifacts_from_releases(
    releases: Iterable[dict[str, Any]],
    *,
    projects: Iterable[str],
    token: str | None,
    opener: Opener,
    quiet: bool = False,
) -> dict[str, list[Artifact]]:
    """Convert raw API release objects into whitelisted index artifacts.

    Prefers each asset's ``digest`` field (``sha256:hex``); downloads the
    asset only when the field is absent or uses another algorithm.

    Args:
        releases: Release objects from :func:`load_releases`.
        projects: Whitelisted distribution names.
        token: Optional bearer token for asset downloads.
        opener: Injectable urlopen-compatible callable.
        quiet: Suppress the per-release progress line.

    Returns:
        Mapping of normalized project name to collected artifacts.
    """
    pages: dict[str, list[Artifact]] = {}
    for release in releases:
        if release.get("draft"):
            continue
        assets = release.get("assets", [])
        counted = 0
        for asset in assets:
            filename = asset.get("name", "")
            project = classify_artifact(filename, projects)
            if project is None:
                continue
            url = asset["browser_download_url"]
            digest = (asset.get("digest") or "").removeprefix("sha256:")
            sha = digest or None
            if sha is None:
                sha = sha256_of_url(url, token=token, opener=opener)
            pages.setdefault(project, []).append(
                Artifact(filename=filename, url=url, sha256=sha)
            )
            counted += 1
        if not quiet and counted:
            print(f"  {release.get('tag_name', '?')}: {counted} artifact(s)")
    return pages


def artifacts_from_wheels(
    wheels_dir: pathlib.Path, *, repo: str, tag: str, projects: Iterable[str]
) -> dict[str, list[Artifact]]:
    """Hash local unpacked artifacts into incremental-mode entries.

    Args:
        wheels_dir: Directory containing ``*.whl`` / ``*.tar.gz`` files.
        repo: ``owner/name`` slug for building release-download URLs.
        tag: Release tag the files belong to.
        projects: Whitelisted distribution names.

    Returns:
        Mapping of normalized project name to artifacts.

    Raises:
        SystemExit: When the directory yields no whitelisted files.
    """
    pages: dict[str, list[Artifact]] = {}
    for path in sorted(wheels_dir.iterdir()):
        if not path.is_file():
            continue
        project = classify_artifact(path.name, projects)
        if project is None:
            continue
        encoded = urllib.parse.quote(path.name)
        url = f"https://github.com/{repo}/releases/download/{tag}/{encoded}"
        pages.setdefault(project, []).append(
            Artifact(filename=path.name, url=url, sha256=sha256_of_file(path))
        )
    if not pages:
        sys.exit(f"error: no whitelisted wheel/sdist files found in {wheels_dir}")
    return pages


def merge(
    existing: dict[str, dict[str, tuple[str, str | None]]],
    new: dict[str, list[Artifact]],
    *,
    replace: bool,
) -> dict[str, dict[str, tuple[str, str | None]]]:
    """Merge collected artifacts into the parsed existing tree.

    Entries deduplicate by artifact URL (a same-version rerun or a
    re-uploaded release asset updates rather than duplicates its line).

    Args:
        existing: Parsed previous tree (empty dict for a rebuild).
        new: Artifacts collected this run, per project.
        replace: When True the existing tree is ignored entirely
            (``--from-releases``); otherwise union-merged.

    Returns:
        Final tree mapping ready for :func:`write_tree`.
    """
    merged: dict[str, dict[str, tuple[str, str | None]]] = (
        {} if replace else {p: dict(e) for p, e in existing.items()}
    )
    for project, artifacts in new.items():
        entries = merged.setdefault(project, {})
        for artifact in artifacts:
            entries[artifact.base_url] = (artifact.filename, artifact.sha256)
    return merged


def _resolve_repo(value: str | None) -> str:
    """Return the ``owner/name`` slug from flag or GITHUB_REPOSITORY.

    Args:
        value: Explicit ``--repo`` value, if given.

    Returns:
        Repository slug.

    Raises:
        SystemExit: When neither source provides one.
    """
    repo = value or os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in repo:
        sys.exit("error: no owner/name repo; pass --repo or set GITHUB_REPOSITORY")
    return repo


def build_parser() -> argparse.ArgumentParser:
    """Construct the command line parser for both operating modes.

    Returns:
        Configured parser (mutually exclusive ``--from-releases`` /
        ``--wheels``).
    """
    parser = argparse.ArgumentParser(
        prog="build_simple_index.py",
        description=__doc__.splitlines()[0],
        epilog=(
            "modes: --from-releases (stateless rebuild via GitHub REST; "
            "production path) or --wheels DIR --tag TAG (incremental merge). "
            "Env: GITHUB_TOKEN (API auth), GITHUB_REPOSITORY (repo slug)."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--from-releases",
        action="store_true",
        help="rebuild the whole tree from all GitHub Releases (production)",
    )
    mode.add_argument(
        "--wheels",
        metavar="DIR",
        type=pathlib.Path,
        help="incremental mode: unpacked wheel/sdist directory",
    )
    parser.add_argument("--tag", help="release tag for --wheels URLs (e.g. v0.2.0)")
    parser.add_argument("--repo", help="owner/name; defaults to GITHUB_REPOSITORY")
    parser.add_argument(
        "--site-out",
        metavar="DIR",
        default=pathlib.Path("simple"),
        type=pathlib.Path,
        help="output tree directory (default: ./simple)",
    )
    parser.add_argument(
        "--projects",
        default=",".join(DEFAULT_PROJECTS),
        help="comma-separated whitelisted distributions "
        f"(default: {','.join(DEFAULT_PROJECTS)})",
    )
    parser.add_argument(
        "--api-base",
        default="https://api.github.com",
        help="GitHub REST API base (default: %(default)s; env GITHUB_API_URL wins)",
    )
    parser.add_argument("--quiet", action="store_true", help="suppress progress output")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point: parse args, run one mode, write the tree.

    Args:
        argv: Argument vector override (defaults to ``sys.argv[1:]``).

    Returns:
        0 on success (SystemExit carries fatal errors).
    """
    args = build_parser().parse_args(argv)
    projects = [p.strip() for p in args.projects.split(",") if p.strip()]
    out: pathlib.Path = args.site_out

    if args.from_releases:
        repo = _resolve_repo(args.repo)
        token = os.environ.get("GITHUB_TOKEN")
        if not token and not args.quiet:
            print("warning: GITHUB_TOKEN unset; unauthenticated API rate limits apply",
                  file=sys.stderr)
        api_base = os.environ.get("GITHUB_API_URL", args.api_base).rstrip("/")
        if not args.quiet:
            print(f"enumerating releases of {repo} via {api_base}")
        releases = load_releases(repo, token=token, api_base=api_base,
                                 opener=urllib.request.urlopen)
        new = artifacts_from_releases(
            releases, projects=projects, token=token,
            opener=urllib.request.urlopen, quiet=args.quiet,
        )
        if out.exists():
            shutil.rmtree(out)  # stateless full rewrite (D2)
        pages = merge({}, new, replace=True)
    else:
        if not args.tag:
            sys.exit("error: --wheels requires --tag")
        repo = _resolve_repo(args.repo)
        if not args.wheels.is_dir():
            sys.exit(f"error: wheels directory not found: {args.wheels}")
        new = artifacts_from_wheels(
            args.wheels, repo=repo, tag=args.tag, projects=projects
        )
        pages = merge(load_existing_tree(out), new, replace=False)

    write_tree(out, pages)
    total = sum(len(entries) for entries in pages.values())
    if not args.quiet:
        listed = ", ".join(f"{p} ({len(e)})" for p, e in sorted(pages.items()))
        print(f"wrote {out}: {total} file(s) across {len(pages)} project(s): {listed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
