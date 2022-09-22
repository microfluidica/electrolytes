import pytest

from typer.testing import CliRunner

from electrolytes import *
from electrolytes.__main__ import app


runner = CliRunner()

def test_ls() -> None:
    result = runner.invoke(app, ["ls"])
    assert result.exit_code == 0
    assert result.stdout


def test_add_and_rm() -> None:
    name = "TEST2322745845"
    try:
        del database[name]
    except KeyError:
        pass
    
    assert name not in database
    with pytest.raises(KeyError):
        database[name]
    
    result = runner.invoke(app, ["add", name.lower(),
                                 "-1", "2", "3",
                                 "-2", "4", "5",
                                 "+1", "6", "-1.5"])

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

    result = runner.invoke(app, ["info", name])
    assert result.exit_code == 0

    result = runner.invoke(app, ["rm", name])
    assert result.exit_code == 0

    with pytest.raises(KeyError):
        del database[name]

    assert name not in database

    result = runner.invoke(app, ["rm", name])
    assert result.exit_code != 0


def test_extra_charges() -> None:
    name = "TEST1328849821"
    try:
        del database[name]
    except KeyError:
        pass
    
    assert name not in database
    with pytest.raises(KeyError):
        database[name]
    
    result = runner.invoke(app, ["add", name,
                                 "+1", "5", "8",
                                 "+2", "7", "6",
                                 "+3", "9", "4",
                                 "+4", "11", "2",
                                 "-1", "1", "10",
                                 "-2", "3", "12"])


    assert result.exit_code == 0
    assert name in database
    c = database[name]
    assert len(c.mobilities()) == 8
    assert len(c.pkas()) == 8
    assert c.mobilities() == pytest.approx([11e-9, 9e-9, 7e-9, 5e-9, 1e-9, 3e-9, 0, 0])
    assert c.pkas() == pytest.approx([2, 4, 6, 8, 10, 12, Constituent._default_pka(-3), Constituent._default_pka(-4)])

    result = runner.invoke(app, ["info", name])
    assert result.exit_code == 0

    result = runner.invoke(app, ["rm", name])
    assert result.exit_code == 0

    with pytest.raises(KeyError):
        del database[name]

    assert name not in database

    result = runner.invoke(app, ["rm", name])
    assert result.exit_code != 0