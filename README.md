# electrolytes

[![CI](https://github.com/microfluidica/electrolytes/actions/workflows/ci.yml/badge.svg)](https://github.com/microfluidica/electrolytes/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/microfluidica/electrolytes/branch/master/graph/badge.svg)](https://codecov.io/gh/microfluidica/electrolytes)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![PyPI](https://img.shields.io/pypi/v/electrolytes)](https://pypi.org/project/electrolytes/)


**electrolytes** provides command-line and programatic access to a database of electrolytes and their properties. It includes 518 components by default (see [credits](#data-credits)). The package covers basic management of the database, including support for storing user-defined electrolytes.

Developed for use with the [`electroMicroTransport`](https://gitlab.com/santiagomarquezd/electroMicroTransport) toolbox for simulation of electromigrative separations.

# Installation

Install with [pip](https://pip.pypa.io/en/stable/):

```bash
$ python3 -m pip install electrolytes
```

**electrolytes** requires Python 3.6 or later, and a relatively recent version of pip (pip may be upgraded with ```python3 -m pip install --upgrade pip```).

# Command-line usage

Invoke the `electrolytes` command-line application to search the database, find the details of a particular component, or to add/remove user-defined components. In your terminal, run:

```bash
$ electrolytes
```

or, alternatively:

```bash
$ python3 -m electrolytes
```

Add the `--help` flag to learn what options are available.

# Python API

The Python API is provided for `electroMicroTransport` case setup scripts.

```python
from electrolytes import database, Properties
```

You can directly use `database` as if it were a `dict` (technically, it is a [`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)), mapping component names to their properties (`Properties` class). Extra methods are also defined:

```python
    def user_defined(self) -> Iterable[str]: ...

    def is_user_defined(self, name: str) -> bool: ...
```

Component names are case insensitive and will be automatically converted to all uppercase. Any components added (or removed) will be saved for the current operating system user. Default components cannot be changed or removed (expect a `ValueError` if you try).

The public stubs of the `Properties` class are:

```python
class Properties:
    def __init__(self,
                 mobilities: Sequence[Optional[float]],
                 pkas: Sequence[Optional[float]]): ...

    def mobilities(self) -> Sequence[float]: ...
    
    def pkas(self) -> Sequence[float]: ...

    def diffusivity(self) -> float: ...
```

with all sequences of length 6 (for +3, +2, +1, -1, -2, -3 respectively). Mobilities and diffusivities are in SI units.

# Data credits

Electrolyte data taken from the Simul 6 [1] application ([homepage](https://simul6.app), [GitHub](https://github.com/hobrasoft/simul6)). The dataset of different electrolytes was originally compiled by Prof. Hirokawa [2].

[1]: GAŠ, Bohuslav; BRAVENEC, Petr. Simul 6: A fast dynamic simulator of electromigration. Electrophoresis, 2021. DOI: [10.1002/elps.202100048](https://doi.org/10.1002/elps.202100048)

[2]: HIROKAWA, Takeshi, et al. Table of isotachophoretic indices: I. Simulated qualitative and quantitative indices of 287 anionic substances in the range ph 3–10. Journal of Chromatography A, 1983, vol. 271, no 2, p. D1-D106. DOI: [10.1016/S0021-9673(00)80225-3](https://doi.org/10.1016/S0021-9673(00)80225-3)