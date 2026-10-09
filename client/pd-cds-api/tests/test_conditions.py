"""Tests for the RunConditions query-parameter model."""

import pytest
from pydantic import ValidationError

from pd_cds_api.conditions import RunConditions


class TestConstruction:
    def test_point_query_defaults(self) -> None:
        conditions = RunConditions(folder="a.b", t0=25034)
        assert conditions.t1 is None
        assert conditions.data_type is None

    def test_accepts_int_and_float_timestamps(self) -> None:
        assert RunConditions(folder="a.b", t0=1).t0 == 1
        assert RunConditions(folder="a.b", t0=1.5, t1=2.5).t1 == 2.5

    def test_folder_is_required(self) -> None:
        with pytest.raises(ValidationError):
            RunConditions(t0=1)  # type: ignore[call-arg]

    def test_non_numeric_timestamp_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RunConditions(folder="a.b", t0="yesterday")  # type: ignore[arg-type]


class TestSchemaDocumentation:
    def test_field_descriptions_present(self) -> None:
        for name, field in RunConditions.model_fields.items():
            assert field.description, f"{name} lacks a description"
