from __future__ import annotations

import contextlib
import subprocess
from time import sleep

from electrolytes import Constituent, database


def test_lock_api_cli() -> None:
    name = "TES7342982891"
    with contextlib.suppress(KeyError):
        del database[name]

    assert name not in database  # ty: ignore[unsupported-operator]

    database.add(Constituent(name=name, u_neg=[2.73], pkas_neg=[3.14]))

    with database:
        proc = subprocess.Popen(["electrolytes", "rm", name])
        sleep(0.1)
        del database[name]
    proc.wait()

    assert proc.returncode != 0
    assert name not in database  # ty: ignore[unsupported-operator]
