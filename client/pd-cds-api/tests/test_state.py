"""Tests for ApiClientState: native-runtime resolution and validation."""

import os

import pytest
from pydantic import ValidationError

from pd_cds_api import state as state_module
from pd_cds_api.state import ApiClientState


class TestFrontierClientPathResolution:
    def test_resolves_to_executable(self) -> None:
        path = ApiClientState().frontier_client_path
        assert os.path.isfile(path)
        assert os.access(path, os.X_OK)

    def test_missing_runtime_raises_clear_error(self) -> None:
        state = ApiClientState(bin_path="pd_cds_api_bin_absent")
        with pytest.raises(FileNotFoundError, match="stage-frontier-client"):
            _ = state.frontier_client_path

    def test_result_is_cached_per_anchor(self) -> None:
        state = ApiClientState()
        assert state.frontier_client_path is state.frontier_client_path

    def test_exec_bit_is_repaired_when_missing(self, monkeypatch) -> None:
        monkeypatch.setattr(state_module.os, "access", lambda *a, **k: False)
        state_module._resolve_client_path.cache_clear()
        try:
            path = ApiClientState().frontier_client_path
            assert path.stat().st_mode & 0o111
        finally:
            state_module._resolve_client_path.cache_clear()


class TestValidation:
    def test_ttl_rejects_out_of_range_level(self) -> None:
        with pytest.raises(ValidationError):
            ApiClientState(frontier_ttl=4)  # type: ignore[arg-type]

    def test_ttl_accepts_all_documented_levels(self) -> None:
        for level in (1, 2, 3):
            assert ApiClientState(frontier_ttl=level).frontier_ttl == level

    def test_invalid_server_url_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ApiClientState(api_server_url="not-a-url")  # type: ignore[arg-type]

    def test_internal_fields_are_frozen(self) -> None:
        state = ApiClientState()
        with pytest.raises(ValidationError):
            state.bin_path = "elsewhere"

    def test_documented_defaults(self) -> None:
        state = ApiClientState()
        assert "dune_runcon_prod" in str(state.api_server_url)
        assert str(state.cache_proxy_url).startswith("http://localhost:3128")
        assert state.format == "csv"
        assert state.frontier_ttl == 2
