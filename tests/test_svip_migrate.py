import pytest
import semantic_version as semver

import svip


def test_migrate(svip_factory):
    sv, appstate = svip_factory()
    assert sv.current_version() == semver.Version('0.0.0')

    # Test upgrade
    sv.migrate(target=semver.Version('2.65.921'))
    expected_data = [
        'up to v0.0.1',
        'up to v0.0.2',
        'up to v0.1.0',
        'up to v0.1.2',
        'up to v0.1.15',
        'up to v2.65.921',
    ]
    assert appstate.get_data() == expected_data

    # Test downgrade
    sv.migrate(target=semver.Version('0.0.2'))
    expected_data = [
        'up to v0.0.1',
        'up to v0.0.2',
        'up to v0.1.0',
        'up to v0.1.2',
        'up to v0.1.15',
        'up to v2.65.921',
        'down from v2.65.921',
        'down from v0.1.15',
        'down from v0.1.2',
        'down from v0.1.0',
    ]
    assert appstate.get_data() == expected_data

    # Test no-op
    sv.migrate(target=semver.Version('0.0.2'))
    assert appstate.get_data() == expected_data


def test_missing_target_argument(svip_factory):
    sv, appstate = svip_factory()

    expected_match = 'sdfsd'
    expected_match = '^parameter "target" is required when "req" is not passed to the constructor$'

    with pytest.raises(ValueError, match=expected_match):
        sv.migrate()


def test_req_in_constructor(svip_factory):
    sv, appstate = svip_factory(req='~0.1')
    sv.migrate()
    expected_data = [
        'up to v0.0.1',
        'up to v0.0.2',
        'up to v0.1.0',
        'up to v0.1.2',
        'up to v0.1.15',
    ]
    assert appstate.get_data() == expected_data


def test_step_no_argument(svip_factory):
    sv, appstate = svip_factory(dirs=['with-step-no-argument'])

    # Test upgrade
    sv.migrate(target=semver.Version('2.65.921'))

    # Test downgrade
    sv.migrate(target=semver.Version('0.0.2'))


def test_no_backup(svip_factory):
    sv, appstate = svip_factory(with_backup=False)

    with pytest.raises(svip.errors.BackupNotImplementedError):
        sv.migrate(target=semver.Version('2.65.921'))

    sv.migrate(target=semver.Version('2.65.921'), save_backup=False)
    expected_data = [
        'up to v0.0.1',
        'up to v0.0.2',
        'up to v0.1.0',
        'up to v0.1.2',
        'up to v0.1.15',
        'up to v2.65.921',
    ]
    assert appstate.get_data() == expected_data


@pytest.mark.parametrize('use_default_implementation', [False, True])
def test_no_backup_restore(svip_factory, use_default_implementation):
    sv, appstate = svip_factory(
        with_backup_restore=None if use_default_implementation else False
    )

    with pytest.raises(svip.errors.RestoreNotImplementedError):
        sv.migrate(
            target=semver.Version('2.65.921'),
            restore_backup=True,
        )


def test_no_guardrails(svip_factory):
    sv, appstate = svip_factory(with_transaction=False)

    with pytest.raises(svip.errors.NoGuardrailsError):
        sv.migrate(target=semver.Version('2.65.921'), save_backup=False)

    sv.migrate(
        target=semver.Version('2.65.921'),
        save_backup=False,
        allow_no_guardrails=True,
    )
    expected_data = [
        'up to v0.0.1',
        'up to v0.0.2',
        'up to v0.1.0',
        'up to v0.1.2',
        'up to v0.1.15',
        'up to v2.65.921',
    ]
    assert appstate.get_data() == expected_data


def test_str_version(svip_factory):
    sv, appstate = svip_factory()
    sv.migrate(target='2.65.921')
    expected_data = [
        'up to v0.0.1',
        'up to v0.0.2',
        'up to v0.1.0',
        'up to v0.1.2',
        'up to v0.1.15',
        'up to v2.65.921',
    ]
    assert appstate.get_data() == expected_data


@pytest.mark.parametrize('error_type', ['returned_value', 'exception'])
@pytest.mark.parametrize('which_call', ['first_call', 'second_call'])
def test_set_version_errors(svip_factory, error_type, which_call):
    def set_version(self, current, target):
        if which_call == 'first_call':
            must_fail = (
                current == semver.Version('0.0.0') and
                target == semver.Version('2.65.921')
            )
        else:
            must_fail = (
                current == semver.Version('2.65.921') and
                target is None
            )

        if must_fail:
            if error_type == 'returned_value':
                return (False,) + self.get_version()
            raise Exception('using exception')
        return super(self.__class__, self).set_version(current, target)

    sv, appstate = svip_factory(asb_overrides={'set_version': set_version})

    previous_snapshot = appstate.get_snapshot()

    if which_call == 'first_call':
        expected_exception = RuntimeError
    else:
        expected_exception = svip.errors.MigrationError


    expected_match = '^'

    if which_call == 'first_call':
        expected_match += r'failed to update version state before migration: '
    else:
        expected_match += r'failed to run migration: '
        expected_match += (
            r'failed to update version information '
            r'after execution of migration steps: '
        )

    if error_type == 'exception':
        expected_match += r'using exception'
    else:
        expected_match += r'unknown reason'

    expected_match += '$'

    with pytest.raises(expected_exception, match=expected_match):
        sv.migrate(target='2.65.921')

    assert previous_snapshot == appstate.get_snapshot()


@pytest.mark.parametrize('cause', ['backup', 'transaction'])
@pytest.mark.parametrize('fail_restore_version', [False, True])
def test_failed_to_start_migration(svip_factory, fail_restore_version, cause):
    asb_overrides = {}

    if cause == 'backup':
        def backup(self, migration_info):
            raise Exception('backup failed on purpose')
        asb_overrides['backup'] = backup
    else:
        def transaction(self):
            raise Exception('transaction creation failed on purpose')
        asb_overrides['transaction'] = transaction

    if fail_restore_version:
        def set_version(self, current, target):
            must_fail = current == semver.Version('0.0.0') and target is None
            if must_fail:
                # Let's take advantage ``cause`` to increase coverage (i.e.,
                # cover both cases: raising exception or returning a tuple with
                # first element set to False)
                if cause == 'backup':
                    raise Exception('version restore failed on purpose')
                else:
                    return False, *self.get_version()
            return super(self.__class__, self).set_version(current, target)
        asb_overrides['set_version'] = set_version

    sv, appstate = svip_factory(asb_overrides=asb_overrides)

    if fail_restore_version:
        expected_exception = svip.errors.RestoreFailedError
        expected_match = r'^failed to restore version after migration error: '
        if cause == 'backup':
            expected_match += r'version restore failed on purpose'
        else:
            expected_match += r'unknown reason'
    elif cause == 'backup':
        expected_exception = svip.errors.BackupFailedError
        expected_match = r'^failed to perform backup: backup failed on purpose$'
    else:
        expected_exception = svip.errors.TransactionFailedError
        expected_match = r'^failed to start transaction: '
        expected_match += r'transaction creation failed on purpose$'

    previous_snapshot = appstate.get_snapshot()

    with pytest.raises(expected_exception, match=expected_match):
        sv.migrate(target='2.65.921')

    if fail_restore_version:
        with pytest.raises(svip.errors.InconsistentStateError):
            sv.migrate(target='2.65.921')
    else:
        assert previous_snapshot == appstate.get_snapshot()


@pytest.mark.parametrize('fail_restore_state', [
    'no_fail',
    'rollback',
    'fail_rollback_but_restore_backup',
    'rollback_and_backup',
])
def test_error_during_migration(svip_factory, fail_restore_state):
    sv, appstate = svip_factory(
        dirs=['with-error-in-step'],
        fail_rollback=fail_restore_state in (
            'rollback',
            'rollback_and_backup',
            'fail_rollback_but_restore_backup',
        ),
        fail_restore_backup=fail_restore_state == 'rollback_and_backup',
    )

    previous_snapshot = appstate.get_snapshot()

    if fail_restore_state in (
        'no_fail',
        'rollback',
        'fail_rollback_but_restore_backup',
    ):
        expected_exception = svip.errors.MigrationError
        expected_match = (
            r'failed to run migration: error running upgrade step to 1\.3\.0: '
            r'Traceback \(most recent call last\):\n'
            r'  File ".*/v1\.3__error-in-step.py", line 6, in up\n'
            r'    raise Exception\(\'exception in up\(\) on purpose\'\)\n'
            r'Exception: exception in up\(\) on purpose\n'
        )
    else:
        expected_exception = svip.errors.RestoreFailedError
        expected_match = (
            r'^failed to restore backup after migration failure: '
            r'backup restore failed on purpose'
        )

    with pytest.raises(expected_exception, match=expected_match):
        sv.migrate(
            target='2.65.921',
            restore_backup=fail_restore_state in (
                'rollback_and_backup',
                'fail_rollback_but_restore_backup',
            ),
        )

    if fail_restore_state in ('no_fail', 'fail_rollback_but_restore_backup'):
        assert previous_snapshot == appstate.get_snapshot()
    else:
        with pytest.raises(svip.errors.InconsistentStateError):
            sv.migrate(target='2.65.921')


def test_error_during_downgrade(svip_factory):
    sv, appstate = svip_factory(
        dirs=['with-error-in-step'],
        current_version=semver.Version('2.65.921'),
    )

    with pytest.raises(
        svip.errors.MigrationError,
        match=(
            r'^failed to run migration: error running downgrade step from 1\.3\.0: '
            r'Traceback \(most recent call last\):\n'
            r'  File ".*/v1\.3__error-in-step.py", line 14, in down\n'
            r'    raise Exception\(\'exception in down\(\) on purpose\'\)\n'
            r'Exception: exception in down\(\) on purpose\n$'
        ),
    ):
        sv.migrate(target='0.0.0')


def test_error_migration_in_progress(migration_in_progress_factory):
    with migration_in_progress_factory(target='2.65.921') as (sv, appstate):
        with pytest.raises(
            svip.errors.MigrationInProgressError,
            match=r'^there is a migration in progress for version 2\.65\.921$',
        ):
            sv.migrate(target='2.65.921')
