import sys
from typing import Tuple, List
if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

import typer
from click import Context, Parameter

from . import database, Constituent


app = typer.Typer()


def complete_name(ctx: Context, param: Parameter, incomplete: str) -> List[str]:
    return [name for name in database if name.startswith(incomplete)]

def complete_name_user_defined(ctx: Context, param: Parameter, incomplete: str) -> List[str]:
    return [name for name in database.user_defined() if name.startswith(incomplete)]


@app.command()
def add(name: Annotated[str, typer.Argument(shell_complete=complete_name_user_defined)],
        p1: Annotated[Tuple[float, float], typer.Option("+1", help="Mobility (*1e-9) and pKa for +1")] = (None, None), # type: ignore
        p2: Annotated[Tuple[float, float], typer.Option("+2", help="Mobility (*1e-9) and pKa for +2")] = (None, None), # type: ignore
        p3: Annotated[Tuple[float, float], typer.Option("+3", help="Mobility (*1e-9) and pKa for +3")] = (None, None), # type: ignore
        p4: Annotated[Tuple[float, float], typer.Option("+4", help="Mobility (*1e-9) and pKa for +4")] = (None, None), # type: ignore
        p5: Annotated[Tuple[float, float], typer.Option("+5", help="Mobility (*1e-9) and pKa for +5")] = (None, None), # type: ignore
        p6: Annotated[Tuple[float, float], typer.Option("+6", help="Mobility (*1e-9) and pKa for +6")] = (None, None), # type: ignore
        m1: Annotated[Tuple[float, float], typer.Option("-1", help="Mobility (*1e-9) and pKa for -1")] = (None, None), # type: ignore
        m2: Annotated[Tuple[float, float], typer.Option("-2", help="Mobility (*1e-9) and pKa for -2")] = (None, None), # type: ignore
        m3: Annotated[Tuple[float, float], typer.Option("-3", help="Mobility (*1e-9) and pKa for -3")] = (None, None), # type: ignore
        m4: Annotated[Tuple[float, float], typer.Option("-4", help="Mobility (*1e-9) and pKa for -4")] = (None, None), # type: ignore
        m5: Annotated[Tuple[float, float], typer.Option("-5", help="Mobility (*1e-9) and pKa for -5")] = (None, None), # type: ignore
        m6: Annotated[Tuple[float, float], typer.Option("-6", help="Mobility (*1e-9) and pKa for -6")] = (None, None), # type: ignore
        force: Annotated[bool, typer.Option("-f", help="Replace any existing user-defined component with the same name")] = False) -> None:
    """Save a user-defined component"""
    name = name.upper()

    if p1[0] is None and m1[0] is None:
        assert p1[1] is None and m1[1] is None
        typer.echo("Error: at least one of the +1 or -1 options is required", err=True)
        raise typer.Exit(code=1)

    neg: List[Tuple[float, float]] = []
    any_omitted = False
    for i,m in enumerate([m1, m2, m3, m4, m5, m6]):
        if m[0] is None:
            assert m[1] is None
            any_omitted = True
        elif any_omitted:
            typer.echo(f"Error: missing charge +{i}", err=True)
            raise typer.Exit(code=1)
        else:
            neg.insert(0, m)

    pos: List[Tuple[float, float]] = []
    any_omitted = False
    for i,p in enumerate([p1, p2, p3, p4, p5, p6]):
        if p[0] is None:
            assert p[1] is None
            any_omitted = True
        elif any_omitted:
            typer.echo(f"Error: missing charge -{i}", err=True)
            raise typer.Exit(code=1)
        else:
            pos.append(p)

    with database._user_constituents_lock:
        if not force and database.is_user_defined(name):
            typer.echo(f"Error: user-defined component {name} already exists (use -f to replace)", err=True)
            raise typer.Exit(code=1)

        try:
            constituent = Constituent(name=name,
                                    u_neg=[x[0] for x in neg],
                                    u_pos=[x[0] for x in pos],
                                    pkas_neg=[x[1] for x in neg],
                                    pkas_pos=[x[1] for x in pos])
            
            try:
                del database[name]
            except KeyError:
                pass

            database.add(constituent)

        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1)


@app.command()
def info(name: Annotated[str, typer.Argument(shell_complete=complete_name)]) -> None:
    """Show the properties of a component"""
    name = name.upper()

    try:
        constituent = database[name]
    except KeyError:
        typer.echo(f"Error: {name}: no such component", err=True)
        raise typer.Exit(code=1)

    charges = list(range(constituent.pos_count, 0, -1)) + list(range(-1, -constituent.neg_count - 1, -1))
    uu = constituent.u_pos[::-1] + constituent.u_neg[::-1]
    pkas = constituent.pkas_pos[::-1] + constituent.pkas_neg[::-1]

    assert len(charges) == len(uu) == len(pkas)
    
    typer.echo(f"Component: {name}")
    if database.is_user_defined(name):
        typer.echo("[user-defined]")
    typer.echo( "                 " + " ".join(f"{c:^+8d}" for c in charges))
    typer.echo( "Mobilities *1e-9:" + " ".join(f"{u:^8.2f}" for u in uu))
    typer.echo( "pKas:            " + " ".join(f"{p:^8.2f}" for p in pkas))
    typer.echo(f"Diffusivity: {constituent.diffusivity():.4e}")


@app.command()
def ls(user_only: Annotated[bool, typer.Option("--user", help="Show only user-defined components")] = False) -> None:
    """List available components"""
    if user_only:
        names = database.user_defined()
    else:
        names = database

    for name in names:
        typer.echo(name)


@app.command()
def rm(names: Annotated[List[str], typer.Argument(shell_complete=complete_name_user_defined)]) -> None:
    """Remove user-defined components"""
    errors_ocurred = False
    for name in names:
        name = name.upper()
        try:
            del database[name]
        except KeyError:
            typer.echo(f"Error: {name}: no such component", err=True)
            errors_ocurred = True
        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            errors_ocurred = True
    
    if errors_ocurred:
        raise typer.Exit(code=-1)


@app.command()
def search(text: str,
           user_only: Annotated[bool, typer.Option("--user", help="Search only user-defined components")] = False) -> None:
    """Search the list of components"""
    text = text.upper()

    if user_only:
        names = list(database.user_defined())
    else:
        names = list(database)

    match_indices = [name.find(text) for name in names]

    for name, index in zip(names, match_indices):
        if index != -1:
            typer.echo(name[0:index] + typer.style(name[index:index+len(text)], bold=True) + name[index+len(text):])


if __name__ == "__main__":
    app(prog_name=__package__)
