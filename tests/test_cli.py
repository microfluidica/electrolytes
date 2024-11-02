import contextlib

import electrolytes
import pytest
from electrolytes import Constituent, database
from electrolytes.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert electrolytes.__version__ in result.stdout


def test_ls() -> None:
    assert "SILVER" in database
    assert not database.is_user_defined("SILVER")

    result = runner.invoke(app, ["ls"])
    assert result.exit_code == 0
    assert "SILVER" in result.stdout

    result = runner.invoke(app, ["ls", "--default"])
    assert result.exit_code == 0
    assert "SILVER" in result.stdout

    result = runner.invoke(app, ["ls", "--user"])
    assert result.exit_code == 0
    assert "SILVER" not in result.stdout


def test_no_rm_default() -> None:
    assert "SILVER" in database
    assert not database.is_user_defined("SILVER")

    result = runner.invoke(app, ["rm", "SILVER"])
    assert result.exit_code != 0

    result = runner.invoke(app, ["rm", "-f", "SILVER"])
    assert result.exit_code != 0


def test_info() -> None:
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert str(len(database)) in result.stdout

    result = runner.invoke(app, ["info", "SILVER", "ZINC"])
    assert result.exit_code == 0
    assert "SILVER" in result.stdout
    assert "ZINC" in result.stdout
    assert "user-defined" not in result.stdout


def test_add_and_rm() -> None:
    name = "TesT2322745845"
    with contextlib.suppress(KeyError):
        del database[name]

    assert name not in database
    with pytest.raises(KeyError):
        database[name]

    result = runner.invoke(app, ["ls"])
    assert result.exit_code == 0
    assert name.upper() not in result.stdout

    result = runner.invoke(app, ["info", name])
    assert result.exit_code != 0

    assert "SILVER" in database
    result = runner.invoke(app, ["info", "SILVER", name])
    assert result.exit_code != 0

    result = runner.invoke(app, ["add", name.lower(), "-2", "4", "5"])
    assert result.exit_code != 0

    result = runner.invoke(
        app, ["add", name.lower(), "-1", "2", "3", "-2", "4", "5", "+1", "6", "-1.5"]
    )

    assert result.exit_code == 0
    assert name in database
    c = database[name]
    assert len(c.mobilities()) == 6
    assert len(c.pkas()) == 6
    assert c.mobilities() == pytest.approx([0, 0, 6e-9, 2e-9, 4e-9, 0])
    assert c.pkas()[0] == Constituent._default_pka(+3)
    assert c.pkas()[1] == Constituent._default_pka(+2)
    assert c.pkas()[2:-1] == pytest.approx([-1.5, 3, 5])
    assert c.pkas()[-1] == Constituent._default_pka(-3)

    result = runner.invoke(
        app, ["add", name.upper(), "-1", "2", "3", "-2", "4", "5", "+1", "6", "-1.5"]
    )
    assert result.exit_code != 0

    result = runner.invoke(app, ["add", "-f", name, "+1", "2", "7", "+2", "4", "5"])
    assert result.exit_code == 0
    assert database[name].pos_count == 2

    result = runner.invoke(app, ["info", name])
    assert result.exit_code == 0
    assert name.upper() in result.stdout
    assert "user-defined" in result.stdout

    result = runner.invoke(app, ["ls"])
    assert result.exit_code == 0
    assert name.upper() in result.stdout

    result = runner.invoke(app, ["ls", "--user"])
    assert result.exit_code == 0
    assert name.upper() in result.stdout

    result = runner.invoke(app, ["ls", "--default"])
    assert result.exit_code == 0
    assert name.upper() not in result.stdout

    result = runner.invoke(app, ["rm", name])
    assert result.exit_code == 0

    with pytest.raises(KeyError):
        del database[name]

    assert name not in database

    result = runner.invoke(app, ["rm", name])
    assert result.exit_code != 0

    result = runner.invoke(app, ["rm", "-f", name])
    assert result.exit_code == 0


def test_extra_charges() -> None:
    name = "TEST1328849821"
    with contextlib.suppress(KeyError):
        del database[name]

    assert name not in database
    with pytest.raises(KeyError):
        database[name]

    result = runner.invoke(
        app,
        [
            "add",
            name,
            "+1",
            "5",
            "8",
            "+2",
            "7",
            "6",
            "+3",
            "9",
            "4",
            "+4",
            "11",
            "2",
            "-1",
            "1",
            "10",
            "-2",
            "3",
            "12",
        ],
    )

    assert result.exit_code == 0
    assert name in database
    c = database[name]
    assert len(c.mobilities()) == 8
    assert len(c.pkas()) == 8
    assert c.mobilities() == pytest.approx([11e-9, 9e-9, 7e-9, 5e-9, 1e-9, 3e-9, 0, 0])
    assert c.pkas() == pytest.approx(
        [2, 4, 6, 8, 10, 12, Constituent._default_pka(-3), Constituent._default_pka(-4)]
    )

    result = runner.invoke(app, ["info", name])
    assert result.exit_code == 0

    result = runner.invoke(app, ["rm", name])
    assert result.exit_code == 0

    with pytest.raises(KeyError):
        del database[name]

    assert name not in database

    result = runner.invoke(app, ["rm", name])
    assert result.exit_code != 0
