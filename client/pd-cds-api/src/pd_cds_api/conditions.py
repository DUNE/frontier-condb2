"""Query-parameter model for a run-conditions request."""

from pydantic import BaseModel, Field


class RunConditions(BaseModel):
    """One conditions query: a folder plus a time point or closed interval.

    A ``t0`` without ``t1`` requests the value in effect at that point
    (wire form ``t=<t0>``); supplying ``t1`` requests the inclusive interval
    ``t0..t1`` (wire form ``t0=..&t1=..``). Time values are experiment
    timestamps (e.g. run numbers), not wall-clock times.

    This model carries *what* to query; connection details live in
    :class:`~pd_cds_api.state.ApiClientState`.
    """

    folder: str = Field(
        description=("Conditions folder path, e.g. ``pdunesp.run_conditionstest``."),
    )
    t0: int | float = Field(
        description=("Beginning timestamp, or sole timestamp when ``t1`` is unset."),
    )
    t1: int | float | None = Field(
        default=None,
        description="End timestamp of a range query; omit for a point query.",
    )
    # tr: int | float | None = None
    data_type: str | None = Field(
        default=None,
        description=(
            "Restrict the payload to a single data type; ``None`` returns "
            "all data types."
        ),
    )
