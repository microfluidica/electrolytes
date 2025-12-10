"""Electrolyte database manager command-line interface."""

import sys
from typing import Annotated

if sys.version_info >= (3, 11):
    from typing import assert_never
else:
    from typing_extensions import assert_never

import cyclopts

from . import Constituent, __version__, database

app = cyclopts.App(help=__doc__, version=__version__)


@app.command
def add(
    name: str,
    *,
    p1: Annotated[tuple[float, float] | None, cyclopts.Parameter(name="+1")] = None,
    p2: Annotated[tuple[float, float] | None, cyclopts.Parameter(name="+2")] = None,
    p3: Annotated[tuple[float, float] | None, cyclopts.Parameter(name="+3")] = None,
    p4: Annotated[tuple[float, float] | None, cyclopts.Parameter(name="+4")] = None,
    p5: Annotated[tuple[float, float] | None, cyclopts.Parameter(name="+5")] = None,
    p6: Annotated[tuple[float, float] | None, cyclopts.Parameter(name="+6")] = None,
    m1: Annotated[tuple[float, float] | None, cyclopts.Parameter(name="-1")] = None,
    m2: Annotated[tuple[float, float] | None, cyclopts.Parameter(name="-2")] = None,
    m3: Annotated[tuple[float, float] | None, cyclopts.Parameter(name="-3")] = None,
    m4: Annotated[tuple[float, float] | None, cyclopts.Parameter(name="-4")] = None,
    m5: Annotated[tuple[float, float] | None, cyclopts.Parameter(name="-5")] = None,
    m6: Annotated[tuple[float, float] | None, cyclopts.Parameter(name="-6")] = None,
    force: bool = False,
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

    if p1 is None and m1 is None:
        print(
            "Error: at least one of the +1 or -1 options is required", file=sys.stderr
        )
        sys.exit(1)

    neg: list[tuple[float, float]] = []
    any_omitted = False
    for i, m in enumerate([m1, m2, m3, m4, m5, m6], start=1):
        if m is None:
            any_omitted = True
        elif any_omitted:
            print(f"Error: missing charge -{i}", file=sys.stederr)
            sys.exit(1)
        else:
            neg.insert(0, m)

    pos: list[tuple[float, float]] = []
    any_omitted = False
    for i, p in enumerate([p1, p2, p3, p4, p5, p6], start=1):
        if p is None:
            any_omitted = True
        elif any_omitted:
            print(f"Error: missing charge +{i}", file=sys.stderr)
            sys.exit(1)
        else:
            pos.append(p)

    constituent = Constituent(
        name=name,
        u_neg=[x[0] for x in neg],
        u_pos=[x[0] for x in pos],
        pkas_neg=[x[1] for x in neg],
        pkas_pos=[x[1] for x in pos],
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
    user: Annotated[bool | None, cyclopts.Parameter(negative="default")] = None,
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
    force: bool = False,
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
    user: Annotated[bool | None, cyclopts.Parameter(negative="default")] = None,
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
