"""Tests for the pd_cds_api package public surface."""

import pd_cds_api
from pd_cds_api import ApiClientState, ApiClientWrapper, RunConditions
from pd_cds_api.conditions import RunConditions as ConditionsModule
from pd_cds_api.state import ApiClientState as StateModule
from pd_cds_api.wrapper import ApiClientWrapper as WrapperModule


class TestPublicSurface:
    def test_all_lists_the_public_names(self) -> None:
        assert pd_cds_api.__all__ == [
            "ApiClientState",
            "ApiClientWrapper",
            "RunConditions",
        ]

    def test_re_exports_are_the_module_classes(self) -> None:
        assert ApiClientState is StateModule
        assert ApiClientWrapper is WrapperModule
        assert RunConditions is ConditionsModule
