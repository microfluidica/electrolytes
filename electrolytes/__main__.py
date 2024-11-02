from typing import Annotated, Optional

import typer

from . import Constituent, __version__, database

app = typer.Typer()


def complete_name(incomplete: str) -> list[str]:
    return [name for name in database if name.startswith(incomplete.upper())]


def complete_name_user_defined(incomplete: str) -> list[str]:
    return [
        name for name in database.user_defined() if name.startswith(incomplete.upper())
    ]


@app.command()
def add(
    name: Annotated[str, typer.Argument(autocompletion=complete_name_user_defined)],
    p1: Annotated[
        tuple[float, float],
        typer.Option("+1", help="Mobility (*1e-9) and pKa for +1", show_default=False),
    ] = (None, None),  # type: ignore [assignment]
    p2: Annotated[
        tuple[float, float],
        typer.Option("+2", help="Mobility (*1e-9) and pKa for +2", show_default=False),
    ] = (None, None),  # type: ignore [assignment]
    p3: Annotated[
        tuple[float, float],
        typer.Option("+3", help="Mobility (*1e-9) and pKa for +3", show_default=False),
    ] = (None, None),  # type: ignore [assignment]
    p4: Annotated[
        tuple[float, float],
        typer.Option("+4", help="Mobility (*1e-9) and pKa for +4", show_default=False),
    ] = (None, None),  # type: ignore [assignment]
    p5: Annotated[
        tuple[float, float],
        typer.Option("+5", help="Mobility (*1e-9) and pKa for +5", show_default=False),
    ] = (None, None),  # type: ignore [assignment]
    p6: Annotated[
        tuple[float, float],
        typer.Option("+6", help="Mobility (*1e-9) and pKa for +6", show_default=False),
    ] = (None, None),  # type: ignore [assignment]
    m1: Annotated[
        tuple[float, float],
        typer.Option("-1", help="Mobility (*1e-9) and pKa for -1", show_default=False),
    ] = (None, None),  # type: ignore [assignment]
    m2: Annotated[
        tuple[float, float],
        typer.Option("-2", help="Mobility (*1e-9) and pKa for -2", show_default=False),
    ] = (None, None),  # type: ignore [assignment]
    m3: Annotated[
        tuple[float, float],
        typer.Option("-3", help="Mobility (*1e-9) and pKa for -3", show_default=False),
    ] = (None, None),  # type: ignore [assignment]
    m4: Annotated[
        tuple[float, float],
        typer.Option("-4", help="Mobility (*1e-9) and pKa for -4", show_default=False),
    ] = (None, None),  # type: ignore [assignment]
    m5: Annotated[
        tuple[float, float],
        typer.Option("-5", help="Mobility (*1e-9) and pKa for -5", show_default=False),
    ] = (None, None),  # type: ignore [assignment]
    m6: Annotated[
        tuple[float, float],
        typer.Option("-6", help="Mobility (*1e-9) and pKa for -6", show_default=False),
    ] = (None, None),  # type: ignore [assignment]
    *,
    force: Annotated[
        bool,
        typer.Option(
            "-f",
            help="Do not prompt before replacing a user-defined component with the same name",
        ),
    ] = False,
) -> None:
    """Store a user-defined component in the database."""
    name = name.upper()

    if p1[0] is None and m1[0] is None:
        assert p1[1] is None
        assert m1[1] is None
        typer.echo("Error: at least one of the +1 or -1 options is required", err=True)
        raise typer.Exit(code=1)

    neg: list[tuple[float, float]] = []
    any_omitted = False
    for i, m in enumerate([m1, m2, m3, m4, m5, m6]):
        if m[0] is None:
            assert m[1] is None
            any_omitted = True
        elif any_omitted:
            typer.echo(f"Error: missing charge -{i}", err=True)
            raise typer.Exit(code=1)
        else:
            neg.insert(0, m)

    pos: list[tuple[float, float]] = []
    any_omitted = False
    for i, p in enumerate([p1, p2, p3, p4, p5, p6]):
        if p[0] is None:
            assert p[1] is None
            any_omitted = True
        elif any_omitted:
            typer.echo(f"Error: missing charge +{i}", err=True)
            raise typer.Exit(code=1)
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
        if name in database:
            if not database.is_user_defined(name):
                typer.echo(f"Error: {name}: is a default component", err=True)
                raise typer.Exit(code=1)

            if not force:
                typer.confirm(f"Replace existing {name}?", abort=True)

            del database[name]

        database.add(constituent)


@app.command()
def info(
    names: Annotated[
        Optional[list[str]],
        typer.Argument(help="Component names", autocompletion=complete_name),
    ] = None,
) -> None:
    """
    Show the properties of components.

    If no names are given, print the number of components in the database.
    """
    if names:
        first = True
        errors_ocurred = False
        for name in names:
            uppercase_name = name.upper()

            try:
                constituent = database[uppercase_name]
            except KeyError:
                typer.echo(f"Error: {uppercase_name}: no such component", err=True)
                errors_ocurred = True
                continue

            charges = list(range(constituent.pos_count, 0, -1)) + list(
                range(-1, -constituent.neg_count - 1, -1)
            )
            uu = constituent.u_pos[::-1] + constituent.u_neg[::-1]
            pkas = constituent.pkas_pos[::-1] + constituent.pkas_neg[::-1]

            assert len(charges) == len(uu) == len(pkas)

            if not first:
                typer.echo()
            typer.echo(f"Component: {uppercase_name}")
            if database.is_user_defined(uppercase_name):
                typer.echo("[user-defined]")
            typer.echo("                    " + " ".join(f"{c:^+8d}" for c in charges))
            typer.echo("Mobilities (*1e-9): " + " ".join(f"{u:^8.2f}" for u in uu))
            typer.echo("pKas:               " + " ".join(f"{p:^8.2f}" for p in pkas))
            typer.echo(f"Diffusivity: {constituent.diffusivity():.4e}")

            first = False

        if errors_ocurred:
            raise typer.Exit(code=1)

    else:
        total = len(database)
        user = len(database.user_defined())
        typer.echo(
            f"{total} components stored in the database ({total - user} default, {user} user-defined)"
        )


@app.command()
def ls(
    *,
    user: Annotated[
        Optional[bool],
        typer.Option(
            "--user/--default", help="List only user-defined/default components"
        ),
    ] = None,
) -> None:
    """List components in the database."""

    if user:
        names = database.user_defined()
    elif user is not None:
        names = [name for name in database if not database.is_user_defined(name)]
    else:
        names = database

    for name in names:
        typer.echo(name)


@app.command()
def rm(
    names: Annotated[
        list[str], typer.Argument(autocompletion=complete_name_user_defined)
    ],
    *,
    force: Annotated[
        Optional[bool], typer.Option("-f", help="Ignore non-existent components")
    ] = False,
) -> None:
    """Remove user-defined components from the database."""
    errors_ocurred = False
    for name in names:
        uppercase_name = name.upper()
        try:
            del database[uppercase_name]
        except KeyError:
            if not force:
                typer.echo(f"Error: {uppercase_name}: no such component", err=True)
                errors_ocurred = True
        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            errors_ocurred = True

    if errors_ocurred:
        raise typer.Exit(code=1)


@app.command()
def search(
    text: str,
    user: Annotated[
        Optional[bool],
        typer.Option(
            "--user/--default", help="Search only user-defined/default components"
        ),
    ] = None,
) -> None:
    """Search for a name in the database."""
    text = text.upper()

    if user:
        names = list(database.user_defined())
    elif user is not None:
        names = [name for name in database if not database.is_user_defined(name)]
    else:
        names = list(database)

    match_indices = [name.find(text) for name in names]

    for name, index in zip(names, match_indices):
        if index != -1:
            typer.echo(
                name[0:index]
                + typer.style(name[index : index + len(text)], bold=True)
                + name[index + len(text) :]
            )


def version_callback(*, show: bool) -> None:
    if show:
        typer.echo(f"{__package__} {__version__}")
        raise typer.Exit


@app.callback()
def common(
    *,
    version: Annotated[
        bool,
        typer.Option(
            "--version", help="Show version and exit.", callback=version_callback
        ),
    ] = False,
) -> None:
    """Database of electrolytes and their properties."""


if __name__ == "__main__":
    app(prog_name=__package__)
