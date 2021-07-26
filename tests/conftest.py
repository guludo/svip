import contextlib
import itertools
import pathlib
import shutil
import threading

import pytest

import appstatemock
import svip


@pytest.fixture
def datadir():
    return pathlib.Path(__file__).parent / 'data'


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


@pytest.fixture
def filenames_dir_factory(datadir, merge_steps_dirs):
    base = datadir / 'step-filenames' / 'valid-step-filenames'
    def factory(*names, inherit_from=base):
        args = [inherit_from] if inherit_from else []
        args += [datadir / 'step-filenames' / name for name in names]
        return merge_steps_dirs(*args)
    return factory


@pytest.fixture
def get_steps_dir_factory(datadir, merge_steps_dirs):
    base = datadir / 'get_steps' / 'base-files'
    def factory(*names, inherit_from=base):
        args = [inherit_from] if inherit_from else []
        args += [datadir / 'get_steps' / name for name in names]
        return merge_steps_dirs(*args)
    return factory


@pytest.fixture
def migrations_with_appstatemock_dir_factory(datadir, merge_steps_dirs):
    base = datadir / 'migrations-with-appstatemock' / 'base-migrations'
    def factory(*names, inherit_from=base):
        args = [inherit_from] if inherit_from else []
        args += [datadir / 'migrations-with-appstatemock' / name for name in names]
        return merge_steps_dirs(*args)
    return factory


@pytest.fixture
def svip_factory(migrations_with_appstatemock_dir_factory):
    def factory(dirs=[], ctx_extra={}, appstate=None, req='', **appstatemock_kw):
        migrations_dir=migrations_with_appstatemock_dir_factory(*dirs)
        if not appstate:
            appstate = appstatemock.AppStateMock(**appstatemock_kw)
        ctx = {'appstate': appstate}
        ctx.update(ctx_extra)
        sv = svip.SVIP(
            asb=appstate.asb,
            req=req,
            conf=svip.SVIPConf(migrations_dir=migrations_dir),
            ctx=ctx,
        )
        return sv, appstate
    return factory


@pytest.fixture
def migration_in_progress_factory(svip_factory):
    @contextlib.contextmanager
    def factory(target='2.65.921'):
        reached_wait_point = threading.Event()
        finished_test = threading.Event()
        sv1, appstate = svip_factory(
            dirs=['with-thread-event-wait'],
            ctx_extra={'events': (reached_wait_point, finished_test)},
        )
        sv2, _ = svip_factory(
            dirs=['with-thread-event-wait'],
            appstate=appstate,
        )

        first_migration_thread = threading.Thread(
            target=sv1.migrate,
            kwargs={'target': target},
        )
        first_migration_thread.start()

        reached_wait_point.wait()

        try:
            yield sv2, appstate
        finally:
            finished_test.set()
            first_migration_thread.join()
    return factory
