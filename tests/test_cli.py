from __future__ import annotations

import contextlib

import pytest

import electrolytes
from electrolytes import Constituent, database
from electrolytes.__main__ import app


def test_version(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        app(["--version"])
    assert exc_info.value.code == 0
    assert electrolytes.__version__ in capsys.readouterr().out


def test_ls(capsys) -> None:
    assert "SILVER" in database
    assert not database.is_user_defined("SILVER")

    with pytest.raises(SystemExit) as exc_info:
        app(["ls"])
    assert exc_info.value.code == 0
    assert "SILVER" in capsys.readouterr().out

    with pytest.raises(SystemExit) as exc_info:
        app(["ls", "--default"])
    assert exc_info.value.code == 0
    assert "SILVER" in capsys.readouterr().out

    with pytest.raises(SystemExit) as exc_info:
        app(["ls", "--user"])
    assert exc_info.value.code == 0
    assert "SILVER" not in capsys.readouterr().out


def test_no_rm_default() -> None:
    assert "SILVER" in database
    assert not database.is_user_defined("SILVER")

    with pytest.raises(SystemExit) as exc_info:
        app(["rm", "SILVER"])
    assert exc_info.value.code != 0

    with pytest.raises(SystemExit) as exc_info:
        app(["rm", "--force", "SILVER"])
    assert exc_info.value.code != 0


def test_info(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        app(["info"])
    assert exc_info.value.code == 0
    assert str(len(database)) in capsys.readouterr().out

    with pytest.raises(SystemExit) as exc_info:
        app(["info", "SILVER", "ZINC"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "SILVER" in out
    assert "ZINC" in out
    assert "user-defined" not in out


def test_add_and_rm(capsys) -> None:
    name = "TesT2322745845"
    with contextlib.suppress(KeyError):
        del database[name]

    assert name not in database
    with pytest.raises(KeyError):
        database[name]

    with pytest.raises(SystemExit) as exc_info:
        app(["ls"])
    assert exc_info.value.code == 0
    assert name.upper() not in capsys.readouterr().out

    with pytest.raises(SystemExit) as exc_info:
        app(["info", name])
    assert exc_info.value.code != 0

    assert "SILVER" in database
    with pytest.raises(SystemExit) as exc_info:
        app(["info", "SILVER", name])
    assert exc_info.value.code != 0

    with pytest.raises(SystemExit) as exc_info:
        app(["add", name.lower(), "-2", "4", "5"])
    assert exc_info.value.code != 0

    with pytest.raises(SystemExit) as exc_info:
        app(["add", name.lower(), "-1", "2", "3", "-2", "4", "5", "+1", "6", "-1.5"])
    assert exc_info.value.code == 0
    assert name in database
    c = database[name]
    assert len(c.mobilities()) == 6
    assert len(c.pkas()) == 6
    assert c.mobilities() == pytest.approx([0, 0, 6e-9, 2e-9, 4e-9, 0])
    assert c.pkas()[0] == Constituent._default_pka(+3)
    assert c.pkas()[1] == Constituent._default_pka(+2)
    assert c.pkas()[2:-1] == pytest.approx([-1.5, 3, 5])
    assert c.pkas()[-1] == Constituent._default_pka(-3)

    with pytest.raises(SystemExit) as exc_info:
        app(["add", name.upper(), "-1", "2", "3", "-2", "4", "5", "+1", "6", "-1.5"])
    assert exc_info.value.code != 0

    with pytest.raises(SystemExit) as exc_info:
        app(["add", "-f", name, "+1", "2", "7", "+2", "4", "5"])
    assert exc_info.value.code == 0
    assert database[name].pos_count == 2

    with pytest.raises(SystemExit) as exc_info:
        app(["info", name])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert name.upper() in out
    assert "user-defined" in out

    with pytest.raises(SystemExit) as exc_info:
        app(["ls"])
    assert exc_info.value.code == 0
    assert name.upper() in capsys.readouterr().out

    with pytest.raises(SystemExit) as exc_info:
        app(["ls", "--user"])
    assert exc_info.value.code == 0
    assert name.upper() in capsys.readouterr().out

    with pytest.raises(SystemExit) as exc_info:
        app(["ls", "--default"])
    assert exc_info.value.code == 0
    assert name.upper() not in capsys.readouterr().out

    with pytest.raises(SystemExit) as exc_info:
        app(["rm", name])
    assert exc_info.value.code == 0
    assert name not in database

    with pytest.raises(KeyError):
        del database[name]

    assert name not in database

    with pytest.raises(SystemExit) as exc_info:
        app(["rm", name])
    assert exc_info.value.code != 0

    with pytest.raises(SystemExit) as exc_info:
        app(["rm", "--force", name])
    assert exc_info.value.code == 0

    with pytest.raises(SystemExit) as exc_info:
        app(["rm", name])
    assert exc_info.value.code != 0


def test_extra_charges() -> None:
    name = "TEST1328849821"
    with contextlib.suppress(KeyError):
        del database[name]

    assert name not in database
    with pytest.raises(KeyError):
        database[name]

    with pytest.raises(SystemExit) as exc_info:
        app(
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
            ]
        )
    assert exc_info.value.code == 0
    assert name in database
    c = database[name]
    assert len(c.mobilities()) == 8
    assert len(c.pkas()) == 8
    assert c.mobilities() == pytest.approx([11e-9, 9e-9, 7e-9, 5e-9, 1e-9, 3e-9, 0, 0])
    assert c.pkas() == pytest.approx(
        [2, 4, 6, 8, 10, 12, Constituent._default_pka(-3), Constituent._default_pka(-4)]
    )

    with pytest.raises(SystemExit) as exc_info:
        app(["info", name])
    assert exc_info.value.code == 0

    with pytest.raises(SystemExit) as exc_info:
        app(["rm", name])
    assert exc_info.value.code == 0

    with pytest.raises(KeyError):
        del database[name]

    assert name not in database

    with pytest.raises(SystemExit) as exc_info:
        app(["rm", name])
    assert exc_info.value.code != 0
