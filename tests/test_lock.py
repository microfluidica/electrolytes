import pytest

import subprocess
from time import sleep

from electrolytes import *


def test_lock_api_cli() -> None:
    name = "TES7342982891"
    try:
        del database[name]
    except KeyError:
        pass
    
    assert name not in database

    database.add(Constituent(name=name,
                             u_neg=[2.73],
                             pkas_neg=[3.14]))

    with database:
        proc = subprocess.Popen(["electrolytes", "rm", name])
        sleep(0.1)
        del database[name]
    proc.wait()

    assert proc.returncode != 0
    assert name not in database
