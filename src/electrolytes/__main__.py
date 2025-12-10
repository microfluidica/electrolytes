"""Electrolyte database manager command-line interface."""

import sys
from dataclasses import dataclass
from typing import Annotated, assert_never

from cyclopts import App, Parameter

from . import Constituent, __version__, database

app = App(help=__doc__, version=__version__)


@Parameter(accepts_keys=False, negative="")
@dataclass
class _Charge:
    charge: int
    mobility: float
    pka: float


@app.command
def add(
    name: str,
    charges: list[_Charge],
    *,
    force: Annotated[bool, Parameter(alias="-f")] = False,
) -> None:
    """
    Store a user-defined component in the database.

    Parameters
    ----------
    name:
        Component name (case-insensitive).
    +1, +2, +3, +4, +5, +6:
        Mobility (*1e-9) and pKa for positive charges.
    -1, -2, -3, -4, -5, -6:
        Mobility (*1e-9) and pKa for negative charges.
    force:
        Do not prompt before replacing a user-defined component with the same name.
    """
    name = name.upper()

    pos_charges: dict[int, tuple[float, float]] = {}
    neg_charges: dict[int, tuple[float, float]] = {}

    for charge in charges:
        if charge.charge > 0:
            if charge.charge in pos_charges:
                print(f"Error: duplicate charge +{charge.charge}", file=sys.stderr)
                sys.exit(1)
            pos_charges[charge.charge] = (charge.mobility, charge.pka)
        elif charge.charge < 0:
            if charge.charge in neg_charges:
                print(f"Error: duplicate charge {charge.charge}", file=sys.stderr)
                sys.exit(1)
            neg_charges[charge.charge] = (charge.mobility, charge.pka)
        else:
            print("Error: charge cannot be zero", file=sys.stderr)
            sys.exit(1)

    if not pos_charges and not neg_charges:
        print("Error: at least one charge is required", file=sys.stderr)
        sys.exit(1)

    u_pos: list[float] = []
    pkas_pos: list[float] = []
    for c in range(1, len(pos_charges) + 1):
        try:
            u, pka = pos_charges[c]
        except KeyError:
            print(f"Error: missing charge {c:+g}", file=sys.stderr)
            sys.exit(1)
        u_pos.append(u)
        pkas_pos.append(pka)
    assert len(u_pos) == len(pos_charges)
    assert len(pkas_pos) == len(pos_charges)

    u_neg: list[float] = []
    pkas_neg: list[float] = []
    for c in range(-len(neg_charges), 0):
        try:
            u, pka = neg_charges[c]
        except KeyError:
            print(f"Error: missing charge {c:+g}", file=sys.stderr)
            sys.exit(1)
        u_neg.append(u)
        pkas_neg.append(pka)
    assert len(u_neg) == len(neg_charges)
    assert len(pkas_neg) == len(neg_charges)

    constituent = Constituent(
        name=name, u_neg=u_neg, u_pos=u_pos, pkas_neg=pkas_neg, pkas_pos=pkas_pos
    )

    with database:
        if name in database:  # type: ignore[unsupported-operator]
            if not database.is_user_defined(name):
                print(f"Error: {name}: is a default component", file=sys.stderr)
                sys.exit(1)

            if not force:
                print(
                    f"Error: {name}: already exists, use --force to overwrite",
                    file=sys.stderr,
                )
                sys.exit(1)

            del database[name]

        database.add(constituent)


@app.command
def info(names: list[str] | None = None) -> None:
    """
    Show the properties of components.

    Parameters
    ----------
    names:
        Component names. If no names are given, print the number of components in the database.
    """
    if names:
        first = True
        errors_ocurred = False
        for name in names:
            uppercase_name = name.upper()

            try:
                constituent = database[uppercase_name]
            except KeyError:
                print(f"Error: {uppercase_name}: no such component", file=sys.stderr)
                errors_ocurred = True
                continue

            charges = list(range(constituent.pos_count, 0, -1)) + list(
                range(-1, -constituent.neg_count - 1, -1)
            )
            uu = constituent.u_pos[::-1] + constituent.u_neg[::-1]
            pkas = constituent.pkas_pos[::-1] + constituent.pkas_neg[::-1]

            assert len(charges) == len(uu) == len(pkas)

            if not first:
                print()
            print(f"Component: {uppercase_name}")
            if database.is_user_defined(uppercase_name):
                print("[user-defined]")
            print("                    " + " ".join(f"{c:^+8d}" for c in charges))
            print("Mobilities (*1e-9): " + " ".join(f"{u:^8.2f}" for u in uu))
            print("pKas:               " + " ".join(f"{p:^8.2f}" for p in pkas))
            print(f"Diffusivity: {constituent.diffusivity():.4e}")

            first = False

        if errors_ocurred:
            sys.exit(1)

    else:
        total = len(database)
        user = len(database.user_defined())
        print(
            f"{total} components stored in the database ({total - user} default, {user} user-defined)"
        )


@app.command
def ls(
    *,
    user: Annotated[bool | None, Parameter(negative="default")] = None,
) -> None:
    """
    List components in the database.

    Parameters
    ----------
    user:
        If --user is given, list only user-defined components.
        If --default is given, list only default components.
        If neither is given, list all components.
    """
    match user:
        case True:
            names = database.user_defined()
        case False:
            names = [name for name in database if not database.is_user_defined(name)]
        case None:
            names = database
        case _:
            assert_never(user)

    for name in names:
        print(name)


@app.command
def rm(
    names: list[str],
    *,
    force: Annotated[bool, Parameter(alias="-f")] = False,
) -> None:
    """Remove user-defined components from the database.

    Parameters
    ----------
    names:
        Component names to remove.
    force:
        Ignore non-existent components.
    """
    errors_ocurred = False
    for name in names:
        uppercase_name = name.upper()
        try:
            del database[uppercase_name]
        except KeyError:
            if not force:
                print(f"Error: {uppercase_name}: no such component", file=sys.stderr)
                errors_ocurred = True
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            errors_ocurred = True

    if errors_ocurred:
        sys.exit(1)


@app.command
def search(
    text: str,
    *,
    user: Annotated[bool | None, Parameter(negative="default")] = None,
) -> None:
    """
    Search for a name in the database.

    Parameters
    ----------
    text:
        Text to search for (case-insensitive).
    user:
        If --user is given, search only user-defined components.
        If --default is given, search only default components.
        If neither is given, search all components.
    """
    text = text.upper()

    match user:
        case True:
            names = list(database.user_defined())
        case False:
            names = [name for name in database if not database.is_user_defined(name)]
        case None:
            names = list(database)
        case _:
            assert_never(user)

    match_indices = [name.find(text) for name in names]

    for name, index in zip(names, match_indices, strict=True):
        if index != -1:
            print(name)


if __name__ == "__main__":
    app()
