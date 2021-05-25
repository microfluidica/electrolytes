import pytest

import electrolytes
from electrolytes import *

def test_version() -> None:
    assert isinstance(electrolytes.__version__, str)


def test_list_components() -> None:
    assert database
    l = list(database)
    assert len(l) == len(database)
    assert isinstance(l[0], str)
    assert l == sorted(l)
    assert "LYSINE" in l
    assert "CYSTINE" in l
    assert "SILVER" in l


def test_get_component() -> None:
    props = database["LYSINE"]
    assert isinstance(props, Properties)
    assert len(props.mobilities()) == 6
    assert len(props.pkas()) == 6
    assert props.diffusivity() == pytest.approx(max(props.mobilities())*8.314*300/96485)


def test_known_component_properties() -> None:
    props = database["CYSTINE"]
    props.mobilities() == pytest.approx([0.0, 5.39e-08, 2.7e-08, 2.7e-08, 5.39e-08, 0.0])
    props.diffusivity() == pytest.approx(1.393350054412603e-09)
    props.pkas() == pytest.approx([-3.0, 1.65, 2.26, 8.405, 9.845, 17])


def test_try_get_nonexistent() -> None:
    with pytest.raises(KeyError):
        database["NONEXISTENT2424612644"]


def test_try_del_nonexistent() -> None:
    with pytest.raises(KeyError):
        del database["NONEXISTENT2424612644"]
        

def test_try_add_default() -> None:
    assert "SILVER" in database
    assert not database.is_user_defined("SILVER")
    assert "SILVER" not in database.user_defined()
    with pytest.raises(ValueError):
        database["SILVER"] = Properties(mobilities=[0, 0, 64.50, 0, 0, 0],
                                        pkas=[-3.00, -2.00, 11.70, 15.00, 16.00, 17.00])