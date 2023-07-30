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
    c = database["LYSINE"]
    assert isinstance(c, Constituent)
    assert c.name == "LYSINE"
    assert c.name in database
    assert c in database
    assert c.name not in database.user_defined()
    assert c not in database.user_defined()
    assert len(c.mobilities()) == 6
    assert len(c.pkas()) == 6
    print(c.mobilities())
    print(c.diffusivity())
    assert c.diffusivity() == pytest.approx(28.60*1e-9*8.314*300/96485)


def test_known_component_properties() -> None:
    c = database["CYSTINE"]
    c.mobilities() == pytest.approx([0.0, 5.39e-08, 2.7e-08, 2.7e-08, 5.39e-08, 0.0])
    c.diffusivity() == pytest.approx(1.393350054412603e-09)
    c.pkas() == pytest.approx([-3.0, 1.65, 2.26, 8.405, 9.845, 17])


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
    with pytest.warns(UserWarning):
        database.add(Constituent(name="SILVER",
                                 u_pos=[64.50],
                                 pkas_pos=[11.70]))
    assert "SILVER" in database
    assert not database.is_user_defined("SILVER")
    assert "SILVER" not in database.user_defined()