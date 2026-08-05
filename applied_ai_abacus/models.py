from __future__ import annotations

from pydantic import BaseModel, StrictInt


class AddNumberRequest(BaseModel):
    number: StrictInt


class SumResponse(BaseModel):
    sum: int
