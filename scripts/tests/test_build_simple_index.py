"""Unit tests for scripts/build_simple_index.py (fixtures + golden HTML).

Goldens live under ``golden/`` next to this file; regenerate deliberately
with ``UPDATE_GOLDENS=1`` and review the diff — they encode the PEP 503
output contract.
"""

import hashlib
import io
import json
import os
import pathlib
import urllib.error

import build_simple_index as bsi
import pytest

REPO = "DUNE/frontier-condb2"
GOLDEN = pathlib.Path(__file__).resolve().parent / "golden"

# Shared corpus: used by BOTH the incremental (--wheels) and the fixture-API
# (--from-releases) tests so their trees compare byte-for-byte (task 2.2).
V020 = {
    "pd_cds_api-0.2.0-py3-none-any.whl": b"api wheel 0.2.0",
    "pd_cds_api_bin-0.2.0-cp314-cp314-manylinux_2_28_x86_64.whl": b"bin x86 0.2.0",
    "pd_cds_api_bin-0.2.0-cp314-cp314-manylinux_2_28_aarch64.whl": b"bin arm 0.2.0",
    "pd_cds_cli-0.2.0-py3-none-any.whl": b"cli wheel 0.2.0",
    "pd-cds-api-0.2.0.tar.gz": b"api sdist",
    "pd-cds-api-bin-0.2.0.tar.gz": b"bin sdist",
    "pd-cds-cli-0.2.0.tar.gz": b"cli sdist",
}
V030 = {
    "pd_cds_cli-0.3.0-py3-none-any.whl": b"cli wheel 0.3.0",
    "pd-cds-cli-0.3.0.tar.gz": b"cli sdist 0.3.0",
}
# Files that must never appear in the index (zip bundles, off-whitelist):
NOISE = {
    "frontier-runtime_0.2.0_x86_64.zip": b"zip bundle",
    "pd_cds_umbrella-0.2.0-py3-none-any.whl": b"not whitelisted",
    "README.md": b"text",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_url(tag: str, name: str) -> str:
    return f"https://github.com/{REPO}/releases/download/{tag}/{name}"


def make_wheels_dir(tmp_path, corpus: dict[str, bytes]) -> pathlib.Path:
    wheels = tmp_path / "wheels"
    wheels.mkdir(parents=True, exist_ok=True)
    for name, data in corpus.items():
        (wheels / name).write_bytes(data)
    return wheels


def release_json(tag: str, corpus: dict[str, bytes], *, draft: bool = False,
                 digestless: str | None = None) -> dict:
    """Fixture release object; `digestless` names one asset lacking digests."""
    assets = []
    for name, data in corpus.items():
        asset = {"name": name, "browser_download_url": download_url(tag, name)}
        if name != digestless:
            asset["digest"] = f"sha256:{sha(data)}"
        assets.append(asset)
    return {"tag_name": tag, "draft": draft, "assets": assets}


def make_opener(pages: dict[str, object]):
    """Fake urlopen serving `pages` keyed by full URL."""

    def open_url(request):
        url = request.full_url
        if url not in pages:
            raise urllib.error.HTTPError(url, 404, "no fixture", None, None)
        payload = pages[url]
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return io.BytesIO(raw)

    return open_url


def releases_url(page: int) -> str:
    return f"https://api.github.com/repos/{REPO}/releases?per_page=100&page={page}"


def install_page_api(releases: list[dict], assets: dict[str, bytes]) -> dict:
    """Build the fake opener registry for one page of releases."""
    pages: dict[str, object] = {releases_url(1): releases, releases_url(2): []}
    for tag_corpus in releases:
        for asset in tag_corpus["assets"]:
            pages[asset["browser_download_url"]] = assets[asset["name"]]
    return pages


def install_urlopen(monkeypatch, pages: dict) -> None:
    monkeypatch.setattr(bsi.urllib.request, "urlopen", make_opener(pages))


def run_incremental(tmp_path, monkeypatch, corpus, tag, out) -> None:
    wheels = make_wheels_dir(tmp_path / f"run-{tag}", corpus)
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert bsi.main(["--wheels", str(wheels), "--tag", tag,
                     "--site-out", str(out), "--quiet"]) == 0


def tree_bytes(root: pathlib.Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def check_or_update_golden(actual: dict[str, bytes], golden_dir: pathlib.Path,
                           monkeypatch) -> None:
    if os.environ.get("UPDATE_GOLDENS"):
        for rel, data in actual.items():
            target = golden_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        pytest.skip(f"goldens refreshed under {golden_dir.name}")
    expected = {
        p.relative_to(golden_dir).as_posix(): p.read_bytes()
        for p in sorted(golden_dir.rglob("*"))
        if p.is_file()
    }
    assert actual == expected


class TestNameHandling:
    def test_normalize_collapses_separators(self) -> None:
        assert bsi.normalize("PD.CDS_api") == "pd-cds-api"
        assert bsi.normalize("pd--cds__api") == "pd-cds-api"

    def test_classify_wheel_and_sdist(self) -> None:
        assert bsi.classify_artifact("pd_cds_cli-0.2.0-py3-none-any.whl",
                                     bsi.DEFAULT_PROJECTS) == "pd-cds-cli"
        assert bsi.classify_artifact("pd-cds-api-bin-0.2.0.tar.gz",
                                     bsi.DEFAULT_PROJECTS) == "pd-cds-api-bin"

    def test_classify_rejects_noise(self) -> None:
        for name in NOISE:
            assert bsi.classify_artifact(name, bsi.DEFAULT_PROJECTS) is None

    def test_version_key_orders_numerically(self) -> None:
        assert bsi.artifact_version("pd_cds_cli-0.10.0-py3-none-any.whl") > \
            bsi.artifact_version("pd_cds_cli-0.2.0-py3-none-any.whl")


class TestIncrementalMode:
    def test_matches_golden_tree(self, tmp_path, monkeypatch) -> None:
        out = tmp_path / "site" / "simple"
        run_incremental(tmp_path, monkeypatch, V020 | NOISE, "v0.2.0", out)
        check_or_update_golden(tree_bytes(out), GOLDEN / "simple", monkeypatch)

    def test_rerun_is_idempotent(self, tmp_path, monkeypatch) -> None:
        out = tmp_path / "simple"
        run_incremental(tmp_path, monkeypatch, V020, "v0.2.0", out)
        first = tree_bytes(out)
        run_incremental(tmp_path / "second", monkeypatch, V020, "v0.2.0", out)
        assert tree_bytes(out) == first  # dedupe by URL, no duplicated lines

    def test_second_tag_merges_without_loss(self, tmp_path, monkeypatch) -> None:
        out = tmp_path / "simple"
        run_incremental(tmp_path, monkeypatch, V020, "v0.2.0", out)
        run_incremental(tmp_path / "b", monkeypatch, V030, "v0.3.0", out)
        cli_page = (out / "pd-cds-cli" / "index.html").read_text()
        assert "v0.2.0" in cli_page and "v0.3.0" in cli_page
        # 0.3.0 sorts newest-first.
        assert cli_page.index("0.3.0") < cli_page.index("0.2.0")
        api_page = (out / "pd-cds-api" / "index.html").read_text()
        assert "0.3.0" not in api_page  # untouched project keeps its entries

    def test_anchors_carry_release_urls_with_sha256(self, tmp_path, monkeypatch) -> None:
        out = tmp_path / "simple"
        run_incremental(tmp_path, monkeypatch, V020, "v0.2.0", out)
        page = (out / "pd-cds-api" / "index.html").read_text()
        expected = f"{download_url('v0.2.0', 'pd_cds_api-0.2.0-py3-none-any.whl')}" \
                   f"#sha256={sha(V020['pd_cds_api-0.2.0-py3-none-any.whl'])}"
        assert expected in page

    def test_wheels_mode_requires_tag(self, tmp_path, monkeypatch) -> None:
        wheels = make_wheels_dir(tmp_path, V020)
        monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
        with pytest.raises(SystemExit):
            bsi.main(["--wheels", str(wheels), "--site-out", str(tmp_path / "o")])

    def test_empty_wheels_dir_fails(self, tmp_path, monkeypatch) -> None:
        wheels = tmp_path / "wheels"
        wheels.mkdir()
        monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
        with pytest.raises(SystemExit):
            bsi.main(["--wheels", str(wheels), "--tag", "v1.0.0",
                      "--site-out", str(tmp_path / "o")])


class TestFromReleasesMode:
    def test_fixture_api_matches_incremental_tree(self, tmp_path, monkeypatch) -> None:
        corpus = V020 | NOISE
        releases = [
            release_json("v0.2.0", corpus),
            release_json("v0.1.9", {}, draft=True),  # drafts skipped
        ]
        pages = install_page_api(releases, corpus)
        install_urlopen(monkeypatch, pages)
        monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        out = tmp_path / "simple"
        assert bsi.main(["--from-releases", "--site-out", str(out), "--quiet"]) == 0

        reference = tmp_path / "ref"
        run_incremental(tmp_path / "w", monkeypatch, corpus, "v0.2.0", reference)
        assert tree_bytes(out) == tree_bytes(reference)  # task 2.2 equality

    def test_digestless_asset_is_downloaded_and_hashed(self, tmp_path,
                                                       monkeypatch) -> None:
        releases = [release_json("v0.2.0", V020,
                                 digestless="pd_cds_cli-0.2.0-py3-none-any.whl")]
        install_urlopen(monkeypatch, install_page_api(releases, V020))
        monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
        out = tmp_path / "simple"
        assert bsi.main(["--from-releases", "--site-out", str(out), "--quiet"]) == 0
        page = (out / "pd-cds-cli" / "index.html").read_text()
        assert f"#sha256={sha(V020['pd_cds_cli-0.2.0-py3-none-any.whl'])}" in page

    def test_paginates_until_short_page(self, tmp_path, monkeypatch) -> None:
        filler = [{"tag_name": f"v0.0.{n}", "draft": False, "assets": []}
                  for n in range(bsi.PAGE_SIZE)]
        releases = [release_json("v0.2.0", V020)]
        pages = {
            releases_url(1): filler,
            releases_url(2): releases,
            releases_url(3): [],
        }
        install_urlopen(monkeypatch, pages)
        monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
        out = tmp_path / "simple"
        assert bsi.main(["--from-releases", "--site-out", str(out), "--quiet"]) == 0
        assert (out / "pd-cds-cli" / "index.html").is_file()

    def test_rebuild_replaces_stale_entries(self, tmp_path, monkeypatch) -> None:
        out = tmp_path / "simple"
        run_incremental(tmp_path, monkeypatch, V030, "v0.3.0", out)
        releases = [release_json("v0.2.0", V020)]
        install_urlopen(monkeypatch, install_page_api(releases, V020))
        monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
        assert bsi.main(["--from-releases", "--site-out", str(out), "--quiet"]) == 0
        cli_page = (out / "pd-cds-cli" / "index.html").read_text()
        assert "0.3.0" not in cli_page  # stateless full rewrite (design D2)
        assert "0.2.0" in cli_page


class TestRenderingContract:
    def test_root_page_lists_normalized_project_dirs(self) -> None:
        html_text = bsi.render_root_page(["pd-cds-cli", "pd-cds-api"])
        assert '<a href="pd-cds-api/">pd-cds-api</a>' in html_text
        assert html_text.index("pd-cds-api") < html_text.index("pd-cds-cli")

    def test_parse_round_trips_generated_pages(self) -> None:
        artifacts = [
            bsi.Artifact("pd_cds_cli-0.2.0-py3-none-any.whl",
                         download_url("v0.2.0", "pd_cds_cli-0.2.0-py3-none-any.whl"),
                         sha(b"cli wheel 0.2.0")),
        ]
        page = bsi.render_project_page("pd-cds-cli", artifacts)
        parsed = bsi.parse_project_page(page)
        assert parsed == {artifacts[0].url:
                          (artifacts[0].filename, artifacts[0].sha256)}
