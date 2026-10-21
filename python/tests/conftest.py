"""Common offline fixtures; all temporary artifacts stay inside the repository."""

import json
import os

import pandas as pd
import pytest

from credit_pack import config as cfg
from credit_pack.config import C
from tests import inputs as fixture


@pytest.fixture
def companyfacts():
    return json.loads(fixture.FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def aging():
    result = pd.DataFrame(fixture.AR_FIXTURE)
    result[C.AFFILIATE] = False
    result[C.FOREIGN] = False
    result[C.CONTRA] = 0.0
    return result


@pytest.fixture(scope="session")
def example_run():
    from credit_pack.run_all import main

    cfg.QA.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = str(cfg.QA)
    return main()
