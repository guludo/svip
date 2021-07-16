import itertools
import pathlib
import shutil

import pytest


@pytest.fixture
def datadir():
    return pathlib.Path(__file__).parent / 'data'


@pytest.fixture
def valid_step_filenames_dir(datadir):
    return datadir / 'valid-step-filenames'


@pytest.fixture
def merge_steps_dirs(tmp_path):
    """
    Fixture that returns a factory to merge steps from one or more directories
    into a new directory.

    This provides the convenience of not needing to create a lot of files for a
    test case: just create the step for the case you want to test and inherit
    step script from another directory.
    """
    counter = itertools.count()
    def factory(*paths):
        dstdir = tmp_path / f'steps-{next(counter)}'
        for p in paths:
            if p is None:
                continue
            shutil.copytree(
                p,
                dstdir,
                dirs_exist_ok=True,
            )
        return dstdir
    return factory
