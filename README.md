# electrolytes

[![CI](https://github.com/microfluidica/electrolytes/actions/workflows/ci.yml/badge.svg)](https://github.com/microfluidica/electrolytes/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/microfluidica/electrolytes/branch/main/graph/badge.svg)](https://codecov.io/gh/microfluidica/electrolytes)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Pydantic v2](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/5697b1e4c4a9790ece607654e6c02a160620c7e1/docs/badge/v2.json)](https://pydantic.dev)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Publish](https://github.com/microfluidica/electrolytes/actions/workflows/pypi-publish.yml/badge.svg)](https://github.com/microfluidica/electrolytes/actions/workflows/pypi-publish.yml)
[![PyPI](https://img.shields.io/pypi/v/electrolytes)](https://pypi.org/project/electrolytes/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/electrolytes)](https://pypi.org/project/electrolytes/)
[![Docker](https://github.com/microfluidica/electrolytes/actions/workflows/docker.yml/badge.svg)](https://github.com/microfluidica/electrolytes/actions/workflows/docker.yml)
[![Docker image](https://img.shields.io/badge/docker%20image-microfluidica%2Felectrolytes-0085a0)](https://hub.docker.com/r/microfluidica/electrolytes/)


**electrolytes** provides command-line and programmatic access to a database of electrolytes and their properties. It includes 518 components by default (see [credits](#data-credits)). The package covers basic management of the database, including support for storing user-defined electrolytes.

## [_electroMicroTransport_](https://gitlab.com/santiagomarquezd/electroMicroTransport)

**electrolytes** is primarily developed as a utility to assist in preparing simulation cases for the [_electroMicroTransport_](https://gitlab.com/santiagomarquezd/electroMicroTransport) toolbox for electromigrative separations. However, it is an independent package and can be installed and used separately.

## Installation

Install with [pip](https://pip.pypa.io/en/stable/):

```bash
$ python3 -m pip install electrolytes
```

## Command-line usage

Invoke the `electrolytes` command-line application to search the database, find the details of a particular component, or to add/remove user-defined components. In your terminal, run:

```bash
$ electrolytes
```

or, alternatively:

```bash
$ python3 -m electrolytes
```

Add the `--help` flag to learn what options are available.

## Python API

The Python API is provided for _electroMicroTransport_ case initialization scripts.

```python
from electrolytes import database, Constituent
```

You can look up components in the `database` as you would with `dict` (with component names as keys), and also add user-defined components with the `add` method (as if `database` were a set). Components are instances of the `Constituent` class. Extra methods are also defined for `database`:

```python

    def user_defined(self) -> Iterable[str]: ...

    def is_user_defined(self, name: str) -> bool: ...
```

The `database` object is also usable as a context manager (i.e. `with database:`), which allows multiple operations to be performed with exclusive access to the database (locking out any other processes for the duration).

`Constituent` names are case insensitive and will be automatically converted to all uppercase. Any instances added to (or removed from) the `database` will be saved for the current operating system user. Default components cannot be changed or removed (expect a `ValueError` if you try).

The public interface of the `Constituent` class is:

```python
class Constituent:
    name: str
    u_neg: Sequence[float] = []  # mobilities for [..., -3, -2, -1], SI units*1e-9
    u_pos: Sequence[float] = []  # mobilities for [+1, +2, +3, ...], SI units*1e-9
    pkas_neg: Sequence[float] = []  # pKas for [..., -3, -2, -1]
    pkas_pos: Sequence[float] = []  # pKas for [+1, +2, +3, ...]

    # Interface for electroMicroTransport
    def mobilities(self) -> Sequence[float]: ...  # for [..., +3, +2, +1, -1, -2, -3, ...], SI units
    def pkas(self) -> Sequence[float]: ...  # for [..., +3, +2, +1, -1, -2, -3, ...]
    # NOTE: the above are padded if needed so that +3 and -3 are always present (len >= 6)
    def diffusivity(self) -> float: ...  # SI units
```

## Data credits

Electrolyte data taken from the Simul 6 application[^simul6] ([homepage](https://simul6.app), [GitHub](https://github.com/hobrasoft/simul6)). The dataset of different electrolytes was originally compiled by Prof. Hirokawa[^Hirokawa].

[^simul6]: GAŠ, Bohuslav; BRAVENEC, Petr. Simul 6: A fast dynamic simulator of electromigration. Electrophoresis, 2021, vol. 42, no. 12-13, pp. 1291-1299. DOI: [10.1002/elps.202100048](https://doi.org/10.1002/elps.202100048)

[^Hirokawa]: HIROKAWA, Takeshi, et al. Table of isotachophoretic indices: I. Simulated qualitative and quantitative indices of 287 anionic substances in the range ph 3–10. Journal of Chromatography A, 1983, vol. 271, no. 2, pp. D1-D106. DOI: [10.1016/S0021-9673(00)80225-3](https://doi.org/10.1016/S0021-9673(00)80225-3)
