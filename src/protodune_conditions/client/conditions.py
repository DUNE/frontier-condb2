from pydantic import BaseModel


class RunConditions(BaseModel):
    folder: str
    t0: int | float
    t1: int | float | None = None
    # tr: int | float | None = None
    data_type: str | None = None
