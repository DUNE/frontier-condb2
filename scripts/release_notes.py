"""Generate human-readable GitHub Release notes and a docs release-history page.

The project ships wheels through a GitHub Pages ``/simple/`` index and cuts a
GitHub Release per version. ``release.yml`` historically used
``--generate-notes``, which yields GitHub's auto-notes: a raw comparison link
plus a sparse PR-title list that is unreadable at this repo's commit density.
The human-meaningful summary already exists in the disciplined
``#<issue> - <what/why>`` commit subjects, so this script derives release bodies
straight from them — no per-PR process overhead.

Two subcommands:

``notes`` (production; the release job)
    Build the release body for one version from the commit history between the
    previous ``v<semver>`` tag and the released revision. A root ``CHANGELOG.md``
    section whose heading names the exact version overrides generation verbatim.
    Exit ``0`` = a body was written; exit ``3`` = nothing derivable (no prior
    tag, or no non-merge commits) so the caller can fall back to auto-notes.

``feed`` (production; every Pages build)
    Render the docs-site release-history page from the Releases API, newest
    first. Best-effort at build time; a committed placeholder covers offline.

Only stdlib is used to keep the official-actions-only, no-new-deps posture.
Network access goes through an injectable ``opener`` (the
``build_simple_index.py`` pattern) so unit tests run hermetically with fixtures;
golden files live under ``scripts/tests/``.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from typing import Any

API_VERSION = "2022-11-28"
USER_AGENT = "pd-cds-release-notes"
PAGE_SIZE = 100
MAX_PAGES = 200  # safety stop; far beyond this project's tag/commit counts
CHANGE_NOTHING = 3  # exit code: "nothing derivable, use the caller's fallback"

_TAG_RE = re.compile(r"^v\d+\.\d+\.\d+$")
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
# ``#<n> - summary`` with an ASCII hyphen or an en/em dash, matching the repo's
# commit-subject convention (see design D2).
_ISSUE_RE = re.compile(r"^#(\d+)\s*[-–—]\s*(.+)$")
_SENTENCE_BREAK = re.compile(r"\.(?:\s|$)")
_SUMMARY_LIMIT = 200

Opener = Callable[[urllib.request.Request], Any]


# --------------------------------------------------------------------------- #
# Versions and tags
# --------------------------------------------------------------------------- #
def parse_version(text: str) -> tuple[int, int, int] | None:
    """Parse a ``vX.Y.Z``/``X.Y.Z`` triple into a comparable tuple.

    Args:
        text: Version string, with or without a leading ``v``.

    Returns:
        ``(major, minor, patch)`` or None when the text is not a plain semver.
    """
    match = _VERSION_RE.match(text.strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def select_prev_tag(tags: Iterable[str], version: str) -> str | None:
    """Return the highest ``v<semver>`` tag strictly below ``version``.

    Name-based comparison keeps the result deterministic (no commit-date
    lookups). Tags that are not plain ``vX.Y.Z`` are ignored.

    Args:
        tags: Tag names (``v0.2.1`` and friends).
        version: The version being released (``0.2.3`` or ``v0.2.3``).

    Returns:
        The previous release tag, or None when no lower tag exists.
    """
    target = parse_version(version)
    if target is None:
        return None
    best_tag: str | None = None
    best: tuple[int, int, int] | None = None
    for tag in tags:
        if not _TAG_RE.match(tag):
            continue
        parsed = parse_version(tag)
        assert parsed is not None  # guaranteed by _TAG_RE
        if parsed < target and (best is None or parsed > best):
            best_tag, best = tag, parsed
    return best_tag


# --------------------------------------------------------------------------- #
# GitHub REST helpers (mirrors build_simple_index.py's opener pattern)
# --------------------------------------------------------------------------- #
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


def _get_json(url: str, *, token: str | None, opener: Opener) -> Any:
    """Fetch and decode one API resource.

    Args:
        url: Fully-qualified API URL.
        token: Optional bearer token.
        opener: Injectable urlopen-compatible callable.

    Returns:
        Decoded JSON body.

    Raises:
        SystemExit: On any transport/HTTP error (fatal to the run).
    """
    try:
        with opener(build_request(url, token)) as response:
            return json.load(response)
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        sys.exit(f"error: GitHub API request failed for {url}: {exc}")


def tags_url(api_base: str, repo: str, page: int) -> str:
    """Return the paginated list-tags endpoint URL."""
    return f"{api_base}/repos/{repo}/tags?per_page={PAGE_SIZE}&page={page}"


def compare_url(api_base: str, repo: str, base: str, head: str, page: int) -> str:
    """Return the paginated compare endpoint URL for ``base...head``."""
    return f"{api_base}/repos/{repo}/compare/{base}...{head}?per_page={PAGE_SIZE}&page={page}"


def fetch_tags(
    repo: str, *, token: str | None, api_base: str, opener: Opener
) -> list[str]:
    """Enumerate every tag name of a repository.

    Args:
        repo: ``owner/name`` slug.
        token: Optional bearer token.
        api_base: REST API base URL.
        opener: Injectable urlopen-compatible callable.

    Returns:
        Tag names across all pages (order preserved).

    Raises:
        SystemExit: When pagination exceeds ``MAX_PAGES``.
    """
    names: list[str] = []
    for page in range(1, MAX_PAGES + 1):
        batch = _get_json(tags_url(api_base, repo, page), token=token, opener=opener)
        names.extend(entry.get("name", "") for entry in batch)
        if len(batch) < PAGE_SIZE:
            return names
    sys.exit(f"error: exceeded {MAX_PAGES} tag pages for {repo}; aborting")


def fetch_compare_commits(
    repo: str,
    base: str,
    head: str,
    *,
    token: str | None,
    api_base: str,
    opener: Opener,
) -> list[dict[str, Any]]:
    """Fetch the commits between two refs, paginated to completion.

    Args:
        repo: ``owner/name`` slug.
        base: Left comparison ref (previous tag).
        head: Right comparison ref (released revision).
        token: Optional bearer token.
        api_base: REST API base URL.
        opener: Injectable urlopen-compatible callable.

    Returns:
        Raw commit objects in chronological order.

    Raises:
        SystemExit: When pagination exceeds ``MAX_PAGES``.
    """
    commits: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        payload = _get_json(
            compare_url(api_base, repo, base, head, page), token=token, opener=opener
        )
        batch = payload.get("commits", [])
        commits.extend(batch)
        total = payload.get("total_commits")
        if len(batch) < PAGE_SIZE or (total is not None and len(commits) >= total):
            return commits
    sys.exit(f"error: exceeded {MAX_PAGES} compare pages for {repo}; aborting")


# --------------------------------------------------------------------------- #
# Commit classification and rendering (notes mode)
# --------------------------------------------------------------------------- #
def is_merge_commit(commit: dict[str, Any]) -> bool:
    """Return True when a compare commit has more than one parent.

    Merge commits are dropped: their ``#<n>`` context is carried by the branch
    commits they merge (design D2).

    Args:
        commit: Raw compare commit object.

    Returns:
        Whether the commit is a merge.
    """
    return len(commit.get("parents", [])) > 1


def commit_subject(commit: dict[str, Any]) -> str:
    """Return the first line of a commit's message.

    Args:
        commit: Raw compare commit object.

    Returns:
        The subject line (empty string when the message is missing).
    """
    message = commit.get("commit", {}).get("message", "")
    return message.splitlines()[0].strip() if message else ""


def cap_summary(text: str, *, limit: int = _SUMMARY_LIMIT) -> str:
    """Shorten a commit subject to one sentence capped at ``limit`` chars.

    Args:
        text: Bullet source text.
        limit: Maximum length before an ellipsis is appended.

    Returns:
        The first sentence, or a word-safe truncation, without trailing space.
    """
    summary = text.strip()
    break_match = _SENTENCE_BREAK.search(summary)
    if break_match:
        summary = summary[: break_match.end()].strip()
    if len(summary) > limit:
        cut = summary[:limit]
        summary = (cut[: cut.rfind(" ")] if " " in cut else cut).rstrip() + "…"
    return summary


def group_commits(
    commits: Sequence[dict[str, Any]],
) -> tuple[list[tuple[int, list[str]]], list[str]]:
    """Group non-merge commits into per-issue bullets plus an "other" bucket.

    Duplicate summaries (revert/reapply churn) collapse within each group while
    first-seen order is preserved.

    Args:
        commits: Raw compare commit objects (chronological).

    Returns:
        ``(groups, others)`` where ``groups`` is ``[(issue, [bullets]), ...]``
        sorted by issue number descending, and ``others`` holds untagged
        subjects.
    """
    by_issue: dict[int, list[str]] = {}
    others: list[str] = []
    for commit in commits:
        if is_merge_commit(commit):
            continue
        subject = commit_subject(commit)
        if not subject:
            continue
        match = _ISSUE_RE.match(subject)
        if match:
            bucket = by_issue.setdefault(int(match.group(1)), [])
            bullet = cap_summary(match.group(2).strip())
            if bullet not in bucket:
                bucket.append(bullet)
        elif subject not in others:
            others.append(cap_summary(subject))
    groups = sorted(by_issue.items(), key=lambda item: item[0], reverse=True)
    return groups, others


def render_notes(
    groups: Sequence[tuple[int, list[str]]],
    others: Sequence[str],
    *,
    repo: str,
    base_tag: str,
    head: str,
) -> str:
    """Render the release body from grouped commits.

    Args:
        groups: ``(issue, bullets)`` pairs, newest issue first.
        others: Unclassifiable commit subjects.
        repo: ``owner/name`` slug (used to build absolute issue/diff links).
        base_tag: Previous release tag named in the heading.
        head: Released revision used in the comparison footer.

    Returns:
        Markdown release body.
    """
    lines: list[str] = [f"## Changes since {base_tag}", ""]
    for issue, bullets in groups:
        lines.append(f"### [#{issue}](https://github.com/{repo}/issues/{issue})")
        lines.append("")
        lines.extend(f"- {bullet}" for bullet in bullets)
        lines.append("")
    if others:
        lines.append("## Other changes")
        lines.append("")
        lines.extend(f"- {subject}" for subject in others)
        lines.append("")
    lines.append(
        f"[Full comparison `{base_tag}...{head}`]"
        f"(https://github.com/{repo}/compare/{base_tag}...{head})"
    )
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------- #
# CHANGELOG.md curation override (notes mode)
# --------------------------------------------------------------------------- #
def load_changelog_override(changelog: pathlib.Path, version: str) -> str | None:
    """Return a ``CHANGELOG.md`` section body for ``version``, if present.

    Recognizes a Keep-a-Changelog heading ``## [X.Y.Z] - <date>`` whose bracketed
    version matches ``version`` exactly; the section runs to the next ``## ``
    heading (or EOF) and is returned verbatim. Malformed headings are ignored.

    Args:
        changelog: Path to the repository root ``CHANGELOG.md``.
        version: Version being released (``0.2.3`` or ``v0.2.3``).

    Returns:
        The curated section body, or None when no matching section exists.
    """
    if not changelog.is_file():
        return None
    wanted = f"## [{version.removeprefix('v')}]"
    lines = changelog.read_text(encoding="utf-8").splitlines()
    body: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = line.startswith(wanted)
            continue
        if inside:
            body.append(line)
    if not inside:
        return None
    text = "\n".join(body).strip("\n")
    return text + "\n" if text.strip() else None


# --------------------------------------------------------------------------- #
# Subcommand runners
# --------------------------------------------------------------------------- #
def _resolve_repo(value: str | None) -> str:
    """Return the ``owner/name`` slug from a flag or ``GITHUB_REPOSITORY``.

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


def _api_base(args: argparse.Namespace) -> str:
    """Return the REST API base (``GITHUB_API_URL`` overrides the flag)."""
    return (os.environ.get("GITHUB_API_URL") or args.api_base).rstrip("/")


def run_notes(args: argparse.Namespace, *, opener: Opener) -> int:
    """Generate a single release body into ``args.out``.

    Args:
        args: Parsed ``notes`` subcommand namespace.
        opener: Injectable urlopen-compatible callable.

    Returns:
        ``0`` when a body was written; ``CHANGE_NOTHING`` when generation is
        impossible (no prior tag / no derivable commits) so the caller falls
        back to GitHub's automatic notes.
    """
    repo = _resolve_repo(args.repo)
    version = args.version

    override = load_changelog_override(args.changelog, version)
    if override is not None:
        args.out.write_text(override, encoding="utf-8")
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    api_base = _api_base(args)
    head = args.ref or os.environ.get("GITHUB_SHA") or "HEAD"

    prev = select_prev_tag(
        fetch_tags(repo, token=token, api_base=api_base, opener=opener), version
    )
    if prev is None:
        return CHANGE_NOTHING

    commits = fetch_compare_commits(
        repo, prev, head, token=token, api_base=api_base, opener=opener
    )
    groups, others = group_commits(commits)
    if not groups and not others:
        return CHANGE_NOTHING

    body = render_notes(groups, others, repo=repo, base_tag=prev, head=head)
    if args.out.parent != pathlib.Path(""):
        args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(body, encoding="utf-8")
    return 0


def run_feed(args: argparse.Namespace, *, opener: Opener) -> int:
    """Render the docs release-history page into ``args.out``, newest first.

    Args:
        args: Parsed ``feed`` subcommand namespace.
        opener: Injectable urlopen-compatible callable.

    Returns:
        ``0`` (an empty history still yields a valid placeholder-shaped page).
    """
    repo = _resolve_repo(args.repo)
    token = os.environ.get("GITHUB_TOKEN")
    api_base = _api_base(args)
    releases = _fetch_releases(repo, token=token, api_base=api_base, opener=opener)
    args.out.write_text(render_history(releases, repo=repo), encoding="utf-8")
    return 0


def _fetch_releases(
    repo: str, *, token: str | None, api_base: str, opener: Opener
) -> list[dict[str, Any]]:
    """Fetch all public releases of a repository (paginated, ascending pages).

    Args:
        repo: ``owner/name`` slug.
        token: Optional bearer token.
        api_base: REST API base URL.
        opener: Injectable urlopen-compatible callable.

    Returns:
        Raw release objects.

    Raises:
        SystemExit: When pagination exceeds ``MAX_PAGES``.
    """
    releases: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        url = f"{api_base}/repos/{repo}/releases?per_page={PAGE_SIZE}&page={page}"
        batch = _get_json(url, token=token, opener=opener)
        releases.extend(batch)
        if len(batch) < PAGE_SIZE:
            return releases
    sys.exit(f"error: exceeded {MAX_PAGES} release pages for {repo}; aborting")


def _release_date(release: dict[str, Any]) -> str:
    """Return a release's ``YYYY-MM-DD`` (published_at, else created_at)."""
    stamp = (release.get("published_at") or release.get("created_at") or "")[:10]
    return stamp


def render_history(releases: Sequence[dict[str, Any]], *, repo: str) -> str:
    """Build the docs release-history page from raw release objects.

    Drafts are skipped; ordering is newest-first by date then tag.

    Args:
        releases: Raw release objects from the Releases API.
        repo: ``owner/name`` slug (used for per-release links).

    Returns:
        Markdown page text.
    """
    visible = [r for r in releases if not r.get("draft")]
    visible.sort(key=lambda r: (_release_date(r), r.get("tag_name", "")), reverse=True)
    lines = [
        "<!-- GENERATED FILE: refreshed from the GitHub Releases API at site",
        "     build time by pages.yml (scripts/release_notes.py feed). The",
        "     committed copy below is a placeholder — do not hand-edit it. -->",
        "",
        "# Release history",
        "",
    ]
    if not visible:
        lines += ["_No releases published yet._", ""]
        return "\n".join(lines)
    for release in visible:
        tag = release.get("tag_name", "?")
        title = release.get("name") or tag
        date = _release_date(release)
        body = (release.get("body") or "").strip()
        date_part = f" ({date})" if date else ""
        lines.append(f"## {tag} — {title}{date_part}")
        lines.append("")
        if body:
            lines.append(body)
            lines.append("")
        url = release.get("html_url") or f"https://github.com/{repo}/releases/tag/{tag}"
        lines.append(f"[View on GitHub]({url})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser with the ``notes`` and ``feed`` subcommands.

    Returns:
        Configured top-level parser.
    """
    parser = argparse.ArgumentParser(
        prog="release_notes.py",
        description=(__doc__ or "").partition("\n")[0],
        epilog=(
            "subcommands: notes (release body for one version) and feed "
            "(docs release-history page). Env: GITHUB_TOKEN, GITHUB_REPOSITORY, "
            "GITHUB_API_URL, GITHUB_SHA."
        ),
    )
    parser.add_argument(
        "--api-base",
        default="https://api.github.com",
        help="GitHub REST API base (default: %(default)s; env GITHUB_API_URL wins)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    notes = sub.add_parser("notes", help="generate one release's note body")
    notes.add_argument(
        "--version", required=True, help="version being released, e.g. 0.2.3"
    )
    notes.add_argument(
        "--ref", help="released revision; defaults to GITHUB_SHA then HEAD"
    )
    notes.add_argument("--repo", help="owner/name; defaults to GITHUB_REPOSITORY")
    notes.add_argument(
        "--out", required=True, type=pathlib.Path, help="body output file"
    )
    notes.add_argument(
        "--changelog",
        type=pathlib.Path,
        default=pathlib.Path("CHANGELOG.md"),
        help="curation override file (default: ./CHANGELOG.md)",
    )

    feed = sub.add_parser("feed", help="render the docs release-history page")
    feed.add_argument("--repo", help="owner/name; defaults to GITHUB_REPOSITORY")
    feed.add_argument(
        "--out", required=True, type=pathlib.Path, help="page output file"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point: dispatch a subcommand and return its process exit code.

    Args:
        argv: Argument vector override (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code (``0`` ok, ``3`` nothing derivable → fallback).
    """
    args = build_parser().parse_args(argv)
    opener = urllib.request.urlopen
    if args.command == "notes":
        return run_notes(args, opener=opener)
    return run_feed(args, opener=opener)


if __name__ == "__main__":
    raise SystemExit(main())
