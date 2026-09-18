from pydantic import BaseModel


class RunConditions(BaseModel):
    folder: str
    t0: int | float
    t1: int | float
    tr: int | float
