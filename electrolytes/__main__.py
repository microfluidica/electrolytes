from typing import Tuple, List

import typer

from . import _APP_NAME, database, Properties


app = typer.Typer()


def complete_name(incomplete: str):
    return [name for name in database if name.startswith(incomplete)]

def complete_name_user_defined(incomplete: str):
    return [name for name in database.user_defined() if name.startswith(incomplete)]


@app.command()
def add(name: str = typer.Argument(..., autocompletion=complete_name_user_defined),
        p1: Tuple[float, float] = typer.Option((None, Properties.DEFAULT_PKAS[2]), "+1", help="Mobility (*1e-9) and pKa for +1"),
        p2: Tuple[float, float] = typer.Option((None, Properties.DEFAULT_PKAS[1]), "+2", help="Mobility (*1e-9) and pKa for +2"),
        p3: Tuple[float, float] = typer.Option((None, Properties.DEFAULT_PKAS[0]), "+3", help="Mobility (*1e-9) and pKa for +3"),
        m1: Tuple[float, float] = typer.Option((None, Properties.DEFAULT_PKAS[3]), "-1", help="Mobility (*1e-9) and pKa for -1"),
        m2: Tuple[float, float] = typer.Option((None, Properties.DEFAULT_PKAS[4]), "-2", help="Mobility (*1e-9) and pKa for -2"),
        m3: Tuple[float, float] = typer.Option((None, Properties.DEFAULT_PKAS[5]), "-3", help="Mobility (*1e-9) and pKa for -3"),
        force: bool = typer.Option(False, "-f", help="Replace any existing user-defined component with the same name")) -> None:
    """Save a user-defined component"""

    mobilities, pkas = zip(*((None, None) if m is None else (m,p) for m,p in (p3, p2, p1, m1, m2, m3)))

    if all(m is None for m in mobilities):
        typer.echo("Error: at least one of the +1 or -1 options is required", err=True)
        raise typer.Exit(code=1)

    if not force and database.is_user_defined(name):
        typer.echo(f"Error: user-defined component {name.upper()} already exists (use -f to replace)", err=True)
        raise typer.Exit(code=1)

    try:
        database[name.upper()] = Properties(mobilities=[m*1e-9 if m is not None else None for m in mobilities],
                                            pkas=pkas)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def info(name: str = typer.Argument(..., autocompletion=complete_name)) -> None:
    """Show the properties of a component"""
    try:
        props = database[name]
        typer.echo(f"Component: {name.upper()}")
        if database.is_user_defined(name):
            typer.echo("[user-defined]")
        typer.echo(f"                  {'+3':^8} {'+2':^8} {'+1':^8} {'-1':^8} {'-2':^8} {'-3':^8}")
        typer.echo( "Mobilities *1e-9: {:^8.2f} {:^8.2f} {:^8.2f} {:^8.2f} {:^8.2f} {:^8.2f}".format(*(m*1e9 for m in props.mobilities())))
        typer.echo( "pKas:             {:^8.2f} {:^8.2f} {:^8.2f} {:^8.2f} {:^8.2f} {:^8.2f}".format(*props.pkas()))
        typer.echo(f"Diffusivity: {props.diffusivity():.4e}")
    except KeyError:
        typer.echo(f"Error: {name}: no such component", err=True)
        raise typer.Exit(code=1)


@app.command()
def ls(user_only: bool=typer.Option(False, "--user", help="Show only user-defined components")) -> None:
    """List available components"""
    if user_only:
        names = database.user_defined()
    else:
        names = database

    for name in names:
        typer.echo(name)


@app.command()
def rm(names: List[str] = typer.Argument(..., autocompletion=complete_name_user_defined)) -> None:
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
           user_only: bool=typer.Option(False, "--user", help="Search only user-defined components")) -> None:
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
    app(prog_name=_APP_NAME)
