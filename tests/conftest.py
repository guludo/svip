import pathlib

import pytest


@pytest.fixture
def datadir():
    return pathlib.Path(__file__).parent / 'data'


@pytest.fixture
def valid_step_filenames_dir(datadir):
    return datadir / 'valid-step-filenames'
