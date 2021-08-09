import contextlib
import datetime

import pytest
import semantic_version as semver

import svip.migration


def generate_tests(
    name,
    asb_fixture_name='asb',
    supports_transaction=True,
    supports_backup=True,
    backup_supports_restore=True,
    supports_version_history=True,
):
    test_functions = {}

    def test_initial_version(request):
        asb = request.getfixturevalue(asb_fixture_name)
        # First current version must be 0.0.0 and target must be None
        assert asb.get_version() == (semver.Version('0.0.0'), None)
    test_functions[f'test_asb_{name}_initial_version'] = test_initial_version


    # The following test checks if the ASB behaves as expected for different
    # cases of calls to `set_version(current, target)`. The parameters below
    # represent a table of cases. The columns are:
    #
    #   - tb_is_none (or tb=0): tells whether the value of `target_before` is
    #      None;
    #
    #   - t_is_none (or t=0): tells whether the value of `target` is None;
    #
    #   - cb_eq_c (cb=c): tells whether `current_before == current`;
    #
    #   - c_eq_tb (c=tb): tells whether `current == target_before`;
    #
    #   - cb: the value for `current_before`;
    #
    #   - tb: the value for `target_before`;
    #
    #   - c: the value for `current`;
    #
    #   - t: the value for `target`.
    @pytest.mark.parametrize(
        'tb_is_none,t_is_none,cb_eq_c,c_eq_tb,cb,tb,c,t',
        [
    #   tb=0  t=0 cb=c c=tb       cb       tb        c        t
         [0,   0,   0,   0, '0.0.0', '0.0.2', '0.0.1', '0.0.2'],
         [0,   0,   0,   1, '0.0.0', '0.0.1', '0.0.1', '0.0.1'],
         [0,   0,   1,   0, '0.0.0', '0.0.1', '0.0.0', '0.0.2'],
    #    [0,   0,   1,   1, -> Impossible situation: (cb=tb) is always False
         [0,   1,   0,   0, '0.0.0', '0.0.1', '0.0.2',    None],
         [0,   1,   0,   1, '0.0.0', '0.0.1', '0.0.1',    None],
         [0,   1,   1,   0, '0.0.0', '0.0.1', '0.0.0',    None],
    #    [0,   1,   1,   1, -> Impossible situation: (cb=tb) is always False
         [1,   0,   0,   0, '0.0.0',    None, '0.0.1', '0.0.1'],
    #    [1,   0,   0,   1, -> Impossible situation: (cb=0) is always False
         [1,   0,   1,   0, '0.0.0',    None, '0.0.0', '0.0.1'],
    #    [1,   0,   1,   1, -> Impossible situation: (cb=tb) is always False
         [1,   1,   0,   0, '0.0.0',    None, '0.0.1',    None],
    #    [1,   1,   0,   1, -> Impossible situation: (cb=0) is always False
         [1,   1,   1,   0, '0.0.1',    None, '0.0.1',    None],
    #    [1,   1,   1,   1, -> Impossible situation: (cb=tb) is always False
        ],
    )
    def test_set_version(
        request, tb_is_none, t_is_none, cb_eq_c, c_eq_tb, cb, tb, c, t
    ):
        asb = request.getfixturevalue(asb_fixture_name)
        cb = semver.Version(cb)
        tb = semver.Version(tb) if tb else None
        c = semver.Version(c)
        t = semver.Version(t) if t else None

        # Let's first make sure that the input values are valid
        assert (tb is None) == tb_is_none
        assert (t is None) == t_is_none
        assert (cb_eq_c) == (cb == c)
        assert (c_eq_tb) == (c == tb)

        arguments_are_valid = (
            (tb is None) != (t is None) and
            (cb != c) == (c == tb and t is None)
        )
        if arguments_are_valid:
            expected_result = True, cb, tb
        else:
            expected_result = False, cb, tb

        # First make version and target without restrictions to simulate the
        # current state
        r = asb.get_test_interface().set_version_no_restrictions(cb, tb)
        assert asb.get_version() == (cb, tb)

        # Now let's test setting version with the restrictions in place
        result = asb.set_version(c, t)
        assert result == expected_result
    test_functions[f'test_asb_{name}_set_version'] = test_set_version

    def test_inconsistency(request):
        asb = request.getfixturevalue(asb_fixture_name)

        # The ASB must be initialized with no inconsistency
        assert asb.get_inconsistency() == None

        asb.register_inconsistency('foo', 'bar')

        assert asb.get_inconsistency() == ('foo', 'bar')

        asb.clear_inconsistency()
        assert asb.get_inconsistency() == None
    test_functions[f'test_asb_{name}_inconsistency'] = test_inconsistency

    def test_version_history(request):
        asb = request.getfixturevalue(asb_fixture_name)
        if not supports_version_history:
            return

        asb.set_version(semver.Version('0.0.0'), semver.Version('0.0.1'))
        asb.set_version(semver.Version('0.0.1'), None)
        asb.set_version(semver.Version('0.0.1'), semver.Version('0.1.0'))
        asb.set_version(semver.Version('0.1.0'), None)
        asb.set_version(semver.Version('0.1.0'), semver.Version('1.0.0'))
        asb.set_version(semver.Version('0.1.0'), None)
        asb.set_version(semver.Version('0.1.0'), semver.Version('1.0.0'))
        asb.set_version(semver.Version('1.0.0'), None)
        asb.set_version(semver.Version('1.0.0'), semver.Version('0.1.0'))
        asb.set_version(semver.Version('0.1.0'), None)

        expected_history_versions = (
            semver.Version('0.0.1'),
            semver.Version('0.1.0'),
            semver.Version('1.0.0'),
            semver.Version('0.1.0'),
        )

        history = asb.get_version_history()
        history_versions, history_timestamps = zip(*history)

        assert history_versions == expected_history_versions
        assert all(isinstance(d, datetime.datetime) for d in history_timestamps)
        assert sorted(history_timestamps) == list(history_timestamps)
    test_functions[f'test_asb_{name}_version_history'] = test_version_history

    @pytest.mark.parametrize('with_migration', ['with_migration', 'without_migration'])
    def test_backup(request, with_migration):
        asb = request.getfixturevalue(asb_fixture_name)

        assert asb.supports_backup() == supports_backup
        if not supports_backup:
            return

        asb.set_version(semver.Version('0.0.0'), semver.Version('0.0.1'))
        asb.set_version(semver.Version('0.0.1'), None)
        asb.set_version(semver.Version('0.0.1'), semver.Version('0.1.0'))
        asb.set_version(semver.Version('0.1.0'), None)
        asb.set_version(semver.Version('0.1.0'), semver.Version('1.0.0'))

        if with_migration == 'with_migration':
            migration_info = svip.migration.MigrationInfo(
                current=semver.Version('0.1.0'),
                target=semver.Version('1.0.0'),
            )
        else:
            migration_info = None

        bkp = asb.backup(migration_info)
        assert isinstance(bkp, svip.AppStateBackup)

        assert asb.backup_supports_restore() == backup_supports_restore
        if not backup_supports_restore:
            return

        asb.set_version(semver.Version('0.1.0'), None)
        asb.set_version(semver.Version('0.1.0'), semver.Version('1.0.0'))
        asb.set_version(semver.Version('1.0.0'), None)
        asb.set_version(semver.Version('1.0.0'), semver.Version('0.1.0'))
        asb.set_version(semver.Version('0.1.0'), None)

        bkp.restore()
        expected = semver.Version('0.1.0'), semver.Version('1.0.0')
        assert asb.get_version() == expected
    test_functions[f'test_asb_{name}_backup'] = test_backup

    @pytest.mark.parametrize('outcome', ['failed_transaction', 'successful_transaction'])
    def test_transaction(request, outcome):
        asb = request.getfixturevalue(asb_fixture_name)

        assert asb.supports_transaction() == supports_transaction
        if not supports_transaction:
            return

        asb.set_version(semver.Version('0.0.0'), semver.Version('0.0.1'))
        asb.set_version(semver.Version('0.0.1'), None)
        asb.set_version(semver.Version('0.0.1'), semver.Version('0.1.0'))
        asb.set_version(semver.Version('0.1.0'), None)
        asb.set_version(semver.Version('0.1.0'), semver.Version('1.0.0'))

        if outcome == 'failed_transaction':
            class CustomException(Exception): pass
            ctx = pytest.raises(
                CustomException,
                match='^testing a failed transaction',
            )
            expected = semver.Version('0.1.0'), semver.Version('1.0.0')
        else:
            ctx = contextlib.nullcontext()
            expected = semver.Version('0.1.0'), None

        with ctx:
            with asb.transaction():
                asb.set_version(semver.Version('0.1.0'), None)
                asb.set_version(semver.Version('0.1.0'), semver.Version('1.0.0'))
                asb.set_version(semver.Version('1.0.0'), None)
                asb.set_version(semver.Version('1.0.0'), semver.Version('0.1.0'))
                asb.set_version(semver.Version('0.1.0'), None)
                if outcome == 'failed_transaction':
                    raise CustomException('testing a failed transaction')

        assert asb.get_version() == expected
    test_functions[f'test_asb_{name}_transaction'] = test_transaction

    return test_functions
