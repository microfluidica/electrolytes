from __future__ import annotations

import importlib.metadata
import itertools
import pkgutil
import sys
from collections.abc import Collection, Iterator, Mapping, Sequence
from contextlib import ContextDecorator, suppress
from functools import cached_property, singledispatchmethod
from pathlib import Path
from typing import TYPE_CHECKING, Annotated
from warnings import warn

from filelock import FileLock
from pydantic import (
    BaseModel,
    Field,
    TypeAdapter,
    ValidationInfo,
    field_validator,
    model_validator,
)
from typer import get_app_dir

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from types import TracebackType

__version__ = importlib.metadata.version(__package__)  # type: ignore[name-defined]


class Constituent(BaseModel, populate_by_name=True, frozen=True):
    id: int | None = None
    name: str
    u_neg: Annotated[
        list[float], Field(alias="uNeg")
    ] = []  # [-neg_count, -neg_count+1, -neg_count+2, ..., -1]
    u_pos: Annotated[
        list[float], Field(alias="uPos")
    ] = []  # [+1, +2, +3, ..., +pos_count]
    pkas_neg: Annotated[
        list[float], Field(alias="pKaNeg")
    ] = []  # [-neg_count, -neg_count+1, -neg_count+2, ..., -1]
    pkas_pos: Annotated[
        list[float], Field(alias="pKaPos")
    ] = []  # [+1, +2, +3, ..., +pos_count]
    neg_count: Annotated[  # ty: ignore[invalid-assignment]
        int, Field(alias="negCount", validate_default=True)
    ] = None
    pos_count: Annotated[  # ty: ignore[invalid-assignment]
        int, Field(alias="posCount", validate_default=True)
    ] = None

    def mobilities(self) -> Sequence[float]:
        n = max(self.neg_count, self.pos_count, 3)
        ret = (
            [0.0] * (n - self.pos_count)
            + [u * 1e-9 for u in self.u_pos[::-1]]
            + [u * 1e-9 for u in self.u_neg[::-1]]
            + [0.0] * (n - self.neg_count)
        )
        assert len(ret) == 2 * n
        return ret

    def pkas(self) -> Sequence[float]:
        n = max(self.neg_count, self.pos_count, 3)
        ret = (
            [self._default_pka(c) for c in range(n, self.pos_count, -1)]
            + self.pkas_pos[::-1]
            + self.pkas_neg[::-1]
            + [self._default_pka(-c) for c in range(self.neg_count + 1, n + 1)]
        )
        assert len(ret) == 2 * n
        return ret

    def diffusivity(self) -> float:
        mobs = []
        with suppress(IndexError):
            mobs.append(self.u_neg[-1] * 1e-9)
        with suppress(IndexError):
            mobs.append(self.u_pos[0] * 1e-9)

        return max(mobs, default=0) * 8.314 * 300 / 96485

    @staticmethod
    def _default_pka(charge: int) -> float:
        assert charge != 0
        if charge < 0:
            return 14 - charge
        return -charge

    @field_validator("name")
    @classmethod
    def _normalize_db1_names(cls, v: str, info: ValidationInfo) -> str:
        context = info.context
        if context is not None and context.get("fix", None) == "db1":
            v = v.replace(" ", "_").replace("Cl-", "CHLORO")
        return v

    @field_validator("name")
    @classmethod
    def _no_whitespace(cls, v: str, _: ValidationInfo) -> str:
        parts = v.split()
        if len(parts) > 1 or len(parts[0]) != len(v):
            msg = "name cannot contain any whitespace"
            raise ValueError(msg)
        return parts[0]

    @field_validator("name")
    @classmethod
    def _all_uppercase(cls, v: str, _: ValidationInfo) -> str:
        if not v.isupper():
            msg = "name must be all uppercase"
            raise ValueError(msg)
        return v

    @field_validator("pkas_neg", "pkas_pos")
    @classmethod
    def _pka_lengths(cls, v: list[float], info: ValidationInfo) -> list[float]:
        field_name = info.field_name
        assert isinstance(field_name, str)
        if len(v) != len(info.data[f"u_{field_name[5:]}"]):
            msg = f"len({field_name}) != len(u_{field_name[5:]})"
            raise ValueError(msg)
        return v

    @field_validator("neg_count", "pos_count", mode="before")
    @classmethod
    def _counts(cls, v: int | None, info: ValidationInfo) -> int:
        field_name = info.field_name
        assert isinstance(field_name, str)
        if v is None:
            v = len(info.data[f"u_{field_name[:3]}"])
        elif v != len(info.data[f"u_{field_name[:3]}"]):
            msg = f"{field_name} != len(u_{field_name[:3]})"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def _pkas_not_increasing(self) -> Constituent:
        pkas = [*self.pkas_neg, *self.pkas_pos]

        if not all(x >= y for x, y in itertools.pairwise(pkas)):
            msg = "pKa values must not increase with charge"
            raise ValueError(msg)

        return self


_StoredConstituents = TypeAdapter(dict[str, list[Constituent]])


def _load_constituents(
    data: bytes, context: dict[str, str] | None = None
) -> list[Constituent]:
    return _StoredConstituents.validate_json(data, context=context)["constituents"]


def _dump_constituents(constituents: list[Constituent]) -> bytes:
    return _StoredConstituents.dump_json(
        {"constituents": constituents}, by_alias=True, indent=4
    )


class _Database(Mapping[str, Constituent], ContextDecorator):
    def __init__(self, user_constituents_file: Path) -> None:
        self._user_constituents_file = user_constituents_file
        self._user_constituents_lock = FileLock(
            self._user_constituents_file.with_suffix(".lock")
        )
        self._user_constituents_dirty = False

    @cached_property
    def _default_constituents(self) -> dict[str, Constituent]:
        assert __package__ is not None
        data = pkgutil.get_data(__package__, "db1.json")
        if data is None:
            msg = "failed to load default constituents"
            raise RuntimeError(msg)
        constituents = _load_constituents(data, context={"fix": "db1"})
        return {c.name: c for c in constituents}

    @cached_property
    def _user_constituents(self) -> dict[str, Constituent]:
        try:
            with self:
                user_data = self._user_constituents_file.read_bytes()
        except OSError:
            return {}
        try:
            user_constituents = _load_constituents(user_data)
        except Exception as e:
            warn(
                f"failed to load user constituents from {self._user_constituents_file}: {type(e).__name__}",
                RuntimeWarning,
                stacklevel=2,
            )
            return {}
        return {c.name: c for c in user_constituents}

    def _invalidate_user_constituents(self) -> None:
        assert not self._user_constituents_dirty
        with suppress(AttributeError):
            del self._user_constituents

    def _save_user_constituents(self) -> None:
        data = _dump_constituents(list(self._user_constituents.values()))
        self._user_constituents_file.parent.mkdir(parents=True, exist_ok=True)
        with self:
            self._user_constituents_file.write_bytes(data)
        self._user_constituents_dirty = False

    def __enter__(self) -> Self:
        if not self._user_constituents_lock.is_locked:
            self._invalidate_user_constituents()
        self._user_constituents_lock.acquire()

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if (
                self._user_constituents_lock.lock_counter == 1
                and self._user_constituents_dirty
            ):
                self._save_user_constituents()
        finally:
            self._user_constituents_lock.release()

    def __iter__(self) -> Iterator[str]:
        yield from sorted([*self._default_constituents, *self._user_constituents])

    def __getitem__(self, name: str) -> Constituent:
        name = name.upper()
        try:
            return self._user_constituents[name]
        except KeyError:
            return self._default_constituents[name]

    def add(self, constituent: Constituent) -> None:
        with self:
            if constituent.name not in self:
                self._user_constituents[constituent.name] = constituent
                self._user_constituents_dirty = True
            else:
                warn(
                    f"{constituent.name}: component was not added (name already exists in database)",
                    stacklevel=2,
                )

    def __delitem__(self, name: str) -> None:
        name = name.upper()
        try:
            with self:
                del self._user_constituents[name]
                self._user_constituents_dirty = True
        except KeyError:
            if name in self._default_constituents:
                msg = f"{name}: cannot remove default component"
                raise ValueError(msg) from None
            raise

    def __len__(self) -> int:
        return len(self._default_constituents) + len(self._user_constituents)

    def user_defined(self) -> Collection[str]:
        return sorted(self._user_constituents)

    @singledispatchmethod
    def __contains__(self, _: object) -> bool:
        return False

    @__contains__.register
    def _(self, obj: str) -> bool:
        name = obj.upper()
        return name in self._default_constituents or name in self._user_constituents

    @__contains__.register
    def _(self, obj: Constituent) -> bool:
        try:
            return obj == self[obj.name]
        except KeyError:
            return False

    def is_user_defined(self, name: str) -> bool:
        name = name.upper()
        return name in self._user_constituents


assert __package__ is not None
database = _Database(Path(get_app_dir(__package__), "user_constituents.json"))
