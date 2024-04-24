# SPDX-License-Identifier: MPL-2.0
import pytest

import svip


def test_error_migration_in_progress(migration_in_progress_factory):
    with migration_in_progress_factory(target='2.65.921') as (sv, appstate):
        with pytest.raises(
            svip.errors.MigrationInProgressError,
            match=r'^there is a migration in progress for version 2\.65\.921$',
        ):
            sv.check('~2.0')


def test_inconsistent_state(svip_factory):
    sv, appstate = svip_factory(
        dirs=['with-error-in-step'],
        with_transaction=False,
        fail_restore_backup=True,
    )

    with pytest.raises(svip.errors.RestoreFailedError):
        sv.migrate(target='2.65.921')

    with pytest.raises(svip.errors.InconsistentStateError):
        sv.check('~2.0')


def test_incompatible_version(svip_factory):
    sv, appstate = svip_factory()

    sv.migrate(target='0.1.15')

    with pytest.raises(svip.errors.IncompatibleVersionError):
        sv.check('~1.0')


def test_compatible_version(svip_factory):
    sv, appstate = svip_factory()

    sv.migrate(target='0.1.15')

    sv.check('~0.1')


def test_missing_spec(svip_factory):
    sv, appstate = svip_factory()

    expected_match = r'^a version specification is required for check\(\): either is as argument for either this method or the constructor$'

    with pytest.raises(ValueError, match=expected_match):
        sv.check()


def test_req_in_constructor(svip_factory):
    sv, appstate = svip_factory(req='~0.1')

    sv.migrate(target='0.1.15')

    sv.check()
