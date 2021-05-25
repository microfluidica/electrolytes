from typing import NamedTuple
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
    props = database[name]
    assert props.mobilities() == pytest.approx([0, 0, 6e-9, 2e-9, 4e-9, 0])
    assert props.pkas()[0] == Properties.DEFAULT_PKAS[0]
    assert props.pkas()[1] == Properties.DEFAULT_PKAS[1]
    assert props.pkas()[2:-1] == pytest.approx([-1.5, 3, 5])
    assert props.pkas()[-1] == Properties.DEFAULT_PKAS[-1]

    result = runner.invoke(app, ["info", name])
    assert result.exit_code == 0

    result = runner.invoke(app, ["rm", name])
    assert result.exit_code == 0

    with pytest.raises(KeyError):
        del database[name]

    assert name not in database

    result = runner.invoke(app, ["rm", name])
    assert result.exit_code != 0
