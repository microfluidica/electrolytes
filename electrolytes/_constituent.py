from collections import abc
from typing import List, Iterator, Iterable

from pydantic import BaseModel, validator, root_validator


class Constituent(BaseModel):
    """constituents.json representation"""
    id: int
    name: str
    negCount: int
    posCount: int
    uNeg: List[float]  # [-n, -n+1, -n+2, ...]
    uPos: List[float]  # [+1, +2, +3, ...]
    pKaNeg: List[float]  # [-n, -n+1, -n+2, ...]
    pKaPos: List[float]  # [+1, +2, +3, ...]

    @validator("uNeg", "pKaNeg")
    def len_neg(cls, v, values, field):
        if len(v) != values["negCount"]:
            raise ValueError(f"len({field}) != negCount")
        return v

    @validator("uPos", "pKaPos")
    def len_pos(cls, v, values, field):
        if len(v) != values["posCount"]:
            raise ValueError(f"len({field}) != posCount")
        return v

    @root_validator
    def pkas_not_increasing(cls, values):
        pkas = [*values["pKaNeg"], *values["pKaPos"]]

        if not all(x>=y for x, y in zip(pkas, pkas[1:])):
            raise ValueError("pKa values must not increase with charge")

        return values
