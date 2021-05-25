import pkgutil
import json
from pathlib import Path
from collections import abc
from typing import Iterable, Iterator, List, Sequence, Dict, Optional

from pydantic import parse_file_as, parse_raw_as
from typer import get_app_dir

from ._constituent import Constituent

_APP_NAME = "electrolytes"

__version__ = "0.1.0"


_USER_CONSTITUENTS_FILE = Path(get_app_dir(_APP_NAME), "user_constituents.json")

def _load_user_constituents() -> Dict[str, Constituent]:
    try:
        constituents = parse_file_as(Dict[str, List[Constituent]], _USER_CONSTITUENTS_FILE)["constituents"]
        return {c.name: c for c in constituents}
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        return {}

def _save_user_constituents(components: Dict[str, Constituent]) -> None:
    _USER_CONSTITUENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _USER_CONSTITUENTS_FILE.open("w") as f:
        json.dump({"constituents": [c.dict() for c in components.values()]}, f)


def _load_default_constituents() -> Dict[str, Constituent]:
    data = pkgutil.get_data(__name__, "data/constituents.json")
    if data is None:
        raise RuntimeError("failed to load default constituents")

    constituents = parse_raw_as(Dict[str, List[Constituent]], data)["constituents"]
    
    for c in constituents:
        if " " in c.name:
            c.name = c.name.replace(" ", "_")
        if "Cl-" in c.name:
            c.name = c.name.replace("Cl-", "CHLORO")

    ret = {c.name: c for c in constituents}

    for omit in {"S1", "S2", "S3", "S4", "S5", "term"}:
        del ret[omit]

    return ret


class Properties:

    def __init__(self, mobilities: Sequence[Optional[float]], pkas: Sequence[Optional[float]]):
        self._check_omitted_charges(mobilities, pkas)
        self._mobilities = mobilities
        self._pkas = pkas


    def mobilities(self) -> Sequence[float]:
        return [m if m is not None else 0 for m in self._mobilities]


    DEFAULT_PKAS = (-3, -2, -1, 15, 16, 17)

    def pkas(self) -> Sequence[float]:
        return [p if p is not None else d for p,d in zip(self._pkas, self.DEFAULT_PKAS)]
    

    def diffusivity(self) -> float:
        return max(self.mobilities())*8.314*300/96485


    @staticmethod
    def _check_omitted_charges(mobilities: Sequence[Optional[float]], pkas: Sequence[Optional[float]]) -> None:
        assert len(mobilities) == 6 and len(pkas) == 6

        negative = (mobilities[3:], pkas[3:])
        positive = (mobilities[:3][::-1], pkas[:3][::-1])

        for mobilities,pkas in negative, positive:
            assert len(mobilities) == 3 and len(pkas) == 3

            any_omitted = False
            for m,p in zip(mobilities, pkas):
                if m is None or p is None:
                    if m is not None or p is not None:
                        raise ValueError("to omit a charge, both mobility and pKa must be None")
                    any_omitted = True
                elif any_omitted:
                    raise ValueError("can only omit charges at the extremes")


    def _as_constituent(self, name: str) -> Constituent:

        uNeg = [m*1e9 for m in self._mobilities[3:][::-1] if m is not None]
        uPos = [m*1e9 for m in self._mobilities[:3][::-1] if m is not None]

        pKaNeg = [p for p in self._pkas[3:][::-1] if p is not None]
        pKaPos = [p for p in self._pkas[:3][::-1] if p is not None]

        return Constituent(id=-1,
                         name=name,
                         negCount=len(uNeg),
                         posCount=len(uPos),
                         uNeg=uNeg,
                         uPos=uPos,
                         pKaNeg=pKaNeg,
                         pKaPos=pKaPos)

    @staticmethod
    def _of_constituent(constituent: Constituent) -> "Properties":
        if constituent.negCount > 3 or constituent.posCount > 3:
            raise ValueError

        mobilities: List[Optional[float]] = [None]*6
        pkas: List[Optional[float]] = [None]*6

        for j in range(constituent.negCount):
            mobilities[3+j] = 1e-9*constituent.uNeg[-j-1]
            pkas[3+j] = constituent.pKaNeg[-j-1]

        for j in range(constituent.posCount):
            mobilities[2-j] = 1e-9*constituent.uPos[j]
            pkas[2-j] = constituent.pKaPos[j]

        return Properties(mobilities=mobilities,
                          pkas=pkas)


    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mobilities={self._mobilities!r}, pkas={self._pkas!r})"


class _Database(abc.MutableMapping):

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


    def __getitem__(self, name: str) -> Properties:
        name = name.upper()
        try:
            return Properties._of_constituent(self._user_constituents[name])
        except KeyError:
            return Properties._of_constituent(self._default_constituents[name])


    def __setitem__(self, name: str, properties: Properties) -> None:
        name = name.upper()
        if name in self._default_constituents:
            raise ValueError(f"{name}: cannot replace default component")

        self._user_constituents[name] = properties._as_constituent(name)
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
