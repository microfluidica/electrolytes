import pkgutil
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence, Dict
from warnings import warn

from pydantic import BaseModel, ConfigDict, Field, field_validator, FieldValidationInfo, model_validator, TypeAdapter
from typer import get_app_dir

_APP_NAME = "electrolytes"

__version__ = "0.2.4"


class Constituent(BaseModel):
    model_config = ConfigDict(populate_by_name=True, validate_default=True)

    id: int = -1
    name: str
    u_neg: List[float] = Field([], alias="uNeg") # [-neg_count, -neg_count+1, -neg_count+2, ..., -1]
    u_pos: List[float] = Field([], alias="uPos") # [+1, +2, +3, ..., +pos_count]
    pkas_neg: List[float] = Field([], alias="pKaNeg") # [-neg_count, -neg_count+1, -neg_count+2, ..., -1]
    pkas_pos: List[float] = Field([], alias="pKaPos") # [+1, +2, +3, ..., +pos_count]
    neg_count: int = Field(-1, alias="negCount")
    pos_count: int = Field(-1, alias="posCount")

    @property
    def charges_neg(self) -> range:
        return range(-self.neg_count, 0)

    @property
    def charges_pos(self) -> range:
        return range(1, self.pos_count + 1)
    
    def mobilities(self) -> Sequence[float]:
        n = max(self.neg_count, self.pos_count, 3)
        ret = [0.0]*(n - self.pos_count) + [u*1e-9 for u in self.u_pos[::-1]] + [u*1e-9 for u in self.u_neg[::-1]] + [0.0]*(n - self.neg_count)
        assert len(ret) == 2*n
        return ret

    def pkas(self) -> Sequence[float]:
        n = max(self.neg_count, self.pos_count, 3)
        ret = [self._default_pka(c) for c in range(n, self.pos_count, -1)] + self.pkas_pos[::-1] + self.pkas_neg[::-1] + [self._default_pka(-c) for c in range(self.neg_count+1, n+1)]
        assert len(ret) == 2*n
        return ret

    def diffusivity(self) -> float:
        mobs = []
        try:
            mobs.append(self.u_neg[-1]*1e-9)
        except IndexError:
            pass
        try:
            mobs.append(self.u_pos[0]*1e-9)
        except IndexError:
            pass

        return max(mobs, default=0)*8.314*300/96485

    @staticmethod
    def _default_pka(charge: int) -> float:
        assert charge != 0
        if charge < 0:
            return 14 - charge
        else:
            return -charge

    @field_validator("pkas_neg", "pkas_pos")
    def pka_lengths(cls, v: List[float], info: FieldValidationInfo) -> List[float]:
        if len(v) != len(info.data[f"u_{info.field_name[5:]}"]):
            raise ValueError(f"len({info.field_name}) != len(u_{info.field_name[5:]})")
        return v
 
    @field_validator("neg_count", "pos_count")
    def counts(cls, v: int, info: FieldValidationInfo) -> int:
        if v == -1:
            v = len(info.data[f"u_{info.field_name[:3]}"])
        elif v != len(info.data[f"u_{info.field_name[:3]}"]):
            raise ValueError(f"{info.field_name} != len(u_{info.field_name[:3]})")
        return v

    @model_validator(mode="after")
    def pkas_not_increasing(self):
        pkas = [*self.pkas_neg, *self.pkas_pos]

        if not all(x>=y for x, y in zip(pkas, pkas[1:])):
            raise ValueError("pKa values must not increase with charge")

        return self


_StoredConstituents = TypeAdapter(Dict[str, List[Constituent]])

_USER_CONSTITUENTS_FILE = Path(get_app_dir(_APP_NAME), "user_constituents.json")

def _load_user_constituents() -> Dict[str, Constituent]:
    try:
        with _USER_CONSTITUENTS_FILE.open("rb") as f:
            data = f.read()
    except FileNotFoundError:
        return {}
    try:
        constituents = _StoredConstituents.validate_json(data)["constituents"]
    except Exception as e:
        warn(f"failed to load user constituents from {_USER_CONSTITUENTS_FILE}: {type(e).__name__}", RuntimeWarning)
        return {}
    return {c.name: c for c in constituents}

def _save_user_constituents(components: Dict[str, Constituent]) -> None:
    data = _StoredConstituents.dump_json({"constituents": list(components.values())})
    _USER_CONSTITUENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _USER_CONSTITUENTS_FILE.open("wb") as f:
        f.write(data)


def _load_default_constituents() -> Dict[str, Constituent]:
    data = pkgutil.get_data(__name__, "db1.json")
    if data is None:
        raise RuntimeError("failed to load default constituents")

    constituents = _StoredConstituents.validate_json(data)["constituents"]

    for c in constituents:
        if " " in c.name:
            c.name = c.name.replace(" ", "_")
        if "Cl-" in c.name:
            c.name = c.name.replace("Cl-", "CHLORO")

    return {c.name: c for c in constituents}


class _Database:

    def __init__(self):
        super().__init__()
        self._loaded_user_constituents = None
        self._loaded_default_constituents = None

    @property
    def _user_constituents(self) -> Dict[str, Constituent]:
        if self._loaded_user_constituents is None:
            self._loaded_user_constituents = _load_user_constituents()
        
        return self._loaded_user_constituents

    @property
    def _default_constituents(self) -> Dict[str, Constituent]:
        if self._loaded_default_constituents is None:
            self._loaded_default_constituents = _load_default_constituents()
        
        return self._loaded_default_constituents


    def __iter__(self) -> Iterator[str]:
        yield from sorted([*self._default_constituents, *self._user_constituents])


    def __getitem__(self, name: str) -> Constituent:
        name = name.upper()
        try:
            return self._user_constituents[name]
        except KeyError:
            return self._default_constituents[name]


    def add(self, constituent: Constituent) -> None:
        if constituent.name not in self:
            self._user_constituents[constituent.name] = constituent
            _save_user_constituents(self._user_constituents)


    def __delitem__(self, name: str) -> None:
        name = name.upper()
        if not name in self._user_constituents:
            if name in self._default_constituents:
                raise ValueError(f"{name}: cannot remove default component")

        del self._user_constituents[name]
        _save_user_constituents(self._user_constituents)


    def __len__(self) -> int:
        return len(self._default_constituents) + len(self._user_constituents)


    def user_defined(self) -> Iterable[str]:
        return sorted(self._user_constituents)

    
    def __contains__(self, name) -> bool:
        if not isinstance(name, str):
            return False
        name = name.upper()
        return name in self._default_constituents or name in self._user_constituents


    def is_user_defined(self, name: str) -> bool:
        name = name.upper()
        return name in self._user_constituents


database = _Database()
