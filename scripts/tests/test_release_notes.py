"""Unit tests for scripts/release_notes.py (fixtures + golden files).

The notes/feed renderers are pure functions of their inputs; the networked
runners are exercised through an injected fake ``urlopen`` (the
``build_simple_index.py`` pattern). Golden bodies encode the release-notes
output contract — regenerate deliberately with ``UPDATE_GOLDENS=1`` and review
the diff.
"""

import io
import json
import os
import pathlib
import urllib.error

import pytest
import release_notes as rn

REPO = "DUNE/frontier-condb2"
GOLDEN = pathlib.Path(__file__).resolve().parent / "golden"
API = "https://api.github.com"


def make_opener(pages: dict[str, object]):
    """Return a fake ``urlopen`` serving ``pages`` keyed by full URL."""

    def open_url(request):
        url = request.full_url
        if url not in pages:
            raise urllib.error.HTTPError(url, 404, "no fixture", None, None)
        payload = pages[url]
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return io.BytesIO(raw)

    return open_url


def install(monkeypatch, pages: dict[str, object]) -> None:
    monkeypatch.setattr(rn.urllib.request, "urlopen", make_opener(pages))
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_API_URL", raising=False)


def check_or_update(actual: str, golden: pathlib.Path) -> None:
    if os.environ.get("UPDATE_GOLDENS"):
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(actual, encoding="utf-8")
        pytest.skip(f"golden refreshed: {golden.name}")
    assert golden.is_file(), f"missing golden {golden}; run UPDATE_GOLDENS=1"
    assert actual == golden.read_text(encoding="utf-8")


# --- fixtures -------------------------------------------------------------- #
def commit(sha: str, message: str, parents: int = 1) -> dict:
    return {
        "sha": sha,
        "parents": [f"p{i}" for i in range(parents)],
        "commit": {"message": message},
    }


TAGS = [
    {"name": "v0.2.3"},
    {"name": "v0.2.2"},
    {"name": "v0.2.1"},
    {"name": "v0.1.0"},
    {"name": "not-semver"},
    {"name": "v0.3"},
]

COMPARE_COMMITS = [
    commit("c1", "#44 - Release only on version change.\n\nBody ignored."),
    commit(
        "c2",
        "#41 - Add post-deploy install smoke to pages.yml "
        + "that is quite long " * 12,
    ),
    commit(
        "c3", "Merge pull request #40 from DUNE/31-zensical-gh-pages-setup", parents=2
    ),  # merge → dropped
    commit("c4", "#41 - Add post-deploy install smoke to pages.yml"),  # dup-ish
    commit("c5", "#39 follow-up - reworded note without a clean dash"),  # → other
    commit("c6", "docs: fix a typo in the runbook"),  # → other
]


def tags_page() -> dict[str, object]:
    return {rn.tags_url(API, REPO, 1): TAGS, rn.tags_url(API, REPO, 2): []}


def compare_page(base: str, head: str) -> dict[str, object]:
    url = rn.compare_url(API, REPO, base, head, 1)
    return {
        url: {"commits": COMPARE_COMMITS, "total_commits": len(COMPARE_COMMITS)},
        rn.compare_url(API, REPO, base, head, 2): [],
    }


# --- pure helpers ---------------------------------------------------------- #
class TestVersionAndTags:
    def test_parse_version(self) -> None:
        assert rn.parse_version("v0.2.3") == (0, 2, 3)
        assert rn.parse_version("0.2.3") == (0, 2, 3)
        assert rn.parse_version("v0.3") is None
        assert rn.parse_version("rc1") is None

    def test_select_prev_tag_is_highest_strictly_below(self) -> None:
        names = [t["name"] for t in TAGS]
        assert rn.select_prev_tag(names, "0.3.0") == "v0.2.3"
        assert rn.select_prev_tag(names, "v0.2.2") == "v0.2.1"
        assert rn.select_prev_tag(names, "0.1.0") is None  # lowest → no prev

    def test_select_prev_tag_ignores_non_semver(self) -> None:
        # "v0.3" (two-part) and "not-semver" must never be chosen.
        assert rn.select_prev_tag(["v0.3", "not-semver", "v1.0.0"], "2.0.0") == "v1.0.0"


class TestClassification:
    def test_merge_commits_dropped(self) -> None:
        groups, others = rn.group_commits([commit("m", "x", parents=2)])
        assert groups == [] and others == []

    def test_issue_grouping_and_other_bucket(self) -> None:
        groups, others = rn.group_commits(COMPARE_COMMITS)
        numbers = [n for n, _ in groups]
        assert numbers == sorted(numbers, reverse=True)
        assert 44 in numbers and 41 in numbers
        # "#39 follow-up -" (dash not adjacent to number) is unclassifiable → other
        assert any("39 follow-up" in o for o in others)
        assert any("typo" in o for o in others)

    def test_duplicate_summaries_collapse(self) -> None:
        groups, _ = rn.group_commits(
            [commit("a", "#9 - Same note."), commit("b", "#9 - Same note.")]
        )
        assert groups == [(9, ["Same note."])]

    def test_cap_summary_first_sentence(self) -> None:
        assert rn.cap_summary("Fix it. And also a second thing.") == "Fix it."

    def test_cap_summary_length_limit(self) -> None:
        capped = rn.cap_summary("word " * 100, limit=40)
        assert capped.endswith("…") and len(capped) <= 41 + 1


class TestRender:
    def test_groups_desc_then_other_last(self) -> None:
        body = rn.render_notes(
            [(44, ["Gate the release."]), (41, ["Add smoke."])],
            ["Stray note"],
            repo=REPO,
            base_tag="v0.2.3",
            head="c0ffee",
        )
        assert body.index("[#44]") < body.index("[#41]") < body.index("Other changes")
        assert f"https://github.com/{REPO}/compare/v0.2.3...c0ffee" in body


# --- notes mode (integration) ---------------------------------------------- #
class TestNotesMode:
    def test_matches_golden(self, tmp_path, monkeypatch) -> None:
        pages = {**tags_page(), **compare_page("v0.2.3", "c0ffee")}
        install(monkeypatch, pages)
        out = tmp_path / "notes.md"
        code = rn.main(
            [
                "notes",
                "--version",
                "0.3.0",
                "--ref",
                "c0ffee",
                "--changelog",
                str(tmp_path / "absent-CHANGELOG.md"),
                "--out",
                str(out),
            ]
        )
        assert code == 0
        check_or_update(
            out.read_text(encoding="utf-8"), GOLDEN / "notes" / "release-0.3.0.md"
        )

    def test_no_prior_tag_exits_3(self, tmp_path, monkeypatch) -> None:
        pages = {
            rn.tags_url(API, REPO, 1): [{"name": "v9.9.9"}],
            rn.tags_url(API, REPO, 2): [],
        }
        install(monkeypatch, pages)
        out = tmp_path / "notes.md"
        code = rn.main(
            [
                "notes",
                "--version",
                "0.1.0",
                "--ref",
                "c0ffee",
                "--changelog",
                str(tmp_path / "absent.md"),
                "--out",
                str(out),
            ]
        )
        assert code == rn.CHANGE_NOTHING
        assert not out.exists()

    def test_empty_diff_exits_3(self, tmp_path, monkeypatch) -> None:
        pages = {**tags_page(), **compare_page("v0.2.3", "c0ffee")}
        # Replace the compare body with only a merge commit → nothing derivable.
        url = rn.compare_url(API, REPO, "v0.2.3", "c0ffee", 1)
        pages[url] = {
            "commits": [commit("m", "Merge x", parents=2)],
            "total_commits": 1,
        }
        install(monkeypatch, pages)
        out = tmp_path / "notes.md"
        code = rn.main(
            [
                "notes",
                "--version",
                "0.3.0",
                "--ref",
                "c0ffee",
                "--changelog",
                str(tmp_path / "absent.md"),
                "--out",
                str(out),
            ]
        )
        assert code == rn.CHANGE_NOTHING


# --- CHANGELOG override (task 1.4) ----------------------------------------- #
class TestChangelogOverride:
    def _write(self, tmp_path: pathlib.Path, text: str) -> pathlib.Path:
        path = tmp_path / "CHANGELOG.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_hit_returns_exact_section(self, tmp_path) -> None:
        path = self._write(
            tmp_path,
            "# Changelog\n\n## [0.3.0] - 2026-10-11\n\nHand-written milestone notes.\n\n"
            "## [0.2.3] - 2026-09-01\n\nOld section.\n",
        )
        # Verbatim section body, stops at the next "## " heading, one trailing newline.
        assert (
            rn.load_changelog_override(path, "0.3.0")
            == "Hand-written milestone notes.\n"
        )

    def test_miss_returns_none(self, tmp_path) -> None:
        path = self._write(tmp_path, "## [0.2.3] - 2026-09-01\n\nOld.\n")
        assert rn.load_changelog_override(path, "0.3.0") is None

    def test_malformed_heading_ignored(self, tmp_path) -> None:
        path = self._write(tmp_path, "## 0.3.0 no brackets\n\nNot a valid heading.\n")
        assert rn.load_changelog_override(path, "0.3.0") is None

    def test_prefix_collisions_not_matched(self, tmp_path) -> None:
        path = self._write(tmp_path, "## [0.3.00] - x\n\nNope.\n")
        assert rn.load_changelog_override(path, "0.3.0") is None

    def test_override_wins_before_any_api_call(self, tmp_path, monkeypatch) -> None:
        # install an opener that 404s everything; override must short-circuit.
        install(monkeypatch, {})
        cl = self._write(tmp_path, "## [0.3.0] - 2026-10-11\n\nCurated body.\n")
        out = tmp_path / "notes.md"
        code = rn.main(
            [
                "notes",
                "--version",
                "0.3.0",
                "--ref",
                "c0ffee",
                "--changelog",
                str(cl),
                "--out",
                str(out),
            ]
        )
        assert code == 0
        assert out.read_text(encoding="utf-8").strip() == "Curated body."


# --- feed mode (task 1.5) -------------------------------------------------- #
RELEASES_FIXTURE = [
    {
        "tag_name": "v0.2.3",
        "name": "v0.2.3",
        "draft": False,
        "published_at": "2026-10-10T20:43:36Z",
        "created_at": "2026-10-10T20:40:00Z",
        "html_url": "https://github.com/DUNE/frontier-condb2/releases/tag/v0.2.3",
        "body": "## Changes since v0.2.2\n\n- Ship something.",
    },
    {
        "tag_name": "v0.2.2",
        "name": None,
        "draft": False,
        "published_at": "2026-10-10T17:17:11Z",
        "created_at": "2026-10-10T17:15:00Z",
        "html_url": "https://github.com/DUNE/frontier-condb2/releases/tag/v0.2.2",
        "body": "",
    },
    {
        "tag_name": "v0.2.1",
        "name": "draft one",
        "draft": True,
        "published_at": None,
        "created_at": "2026-10-10T12:00:00Z",
        "html_url": "https://github.com/DUNE/frontier-condb2/releases/tag/v0.2.1",
        "body": "should not appear",
    },
]


def releases_pages() -> dict[str, object]:
    return {
        f"{API}/repos/{REPO}/releases?per_page=100&page=1": RELEASES_FIXTURE,
        f"{API}/repos/{REPO}/releases?per_page=100&page=2": [],
    }


class TestFeedMode:
    def test_matches_golden_newest_first_drops_drafts(
        self, tmp_path, monkeypatch
    ) -> None:
        install(monkeypatch, releases_pages())
        out = tmp_path / "release-notes.md"
        assert rn.main(["feed", "--out", str(out)]) == 0
        text = out.read_text(encoding="utf-8")
        check_or_update(text, GOLDEN / "release-notes.md")
        assert "v0.2.1" not in text  # draft skipped
        assert text.index("v0.2.3") < text.index("v0.2.2")  # newest first
        assert "# Release history" in text

    def test_empty_history_yields_placeholder_page(self, tmp_path, monkeypatch) -> None:
        install(
            monkeypatch,
            {
                f"{API}/repos/{REPO}/releases?per_page=100&page=1": [],
                f"{API}/repos/{REPO}/releases?per_page=100&page=2": [],
            },
        )
        out = tmp_path / "release-notes.md"
        assert rn.main(["feed", "--out", str(out)]) == 0
        assert "# Release history" in out.read_text(encoding="utf-8")
