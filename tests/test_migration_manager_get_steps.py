import pytest
import semantic_version as semver

import svip.errors
import svip.migration


def test_valid_formats(get_steps_dir_factory):
    manager = svip.migration.MigrationManager(get_steps_dir_factory())

    steps = manager.get_steps(
        current=semver.Version('0.0.0'),
        target=manager.get_latest_match(semver.NpmSpec('*')),
    )
    ids_from_metadata = [step.metadata['id_for_test'] for step in steps]
    expected_ids = ['v1', 'v2', 'v3', 'v4', 'v5']
    assert ids_from_metadata == expected_ids


def test_with_single_parameters(get_steps_dir_factory):
    manager = svip.migration.MigrationManager(
        get_steps_dir_factory('with-single-parameter')
    )
    list(manager.get_steps(
        current=semver.Version('0.0.0'),
        target=manager.get_latest_match(semver.NpmSpec('*')),
    ))


def test_irreversible_step(get_steps_dir_factory):
    manager = svip.migration.MigrationManager(
        get_steps_dir_factory('irreversible-step'),
    )

    with pytest.raises(
        svip.errors.IrreversibleStepError,
        match=r'^downgrade is not possible because .*/v3\.1__irreversible-step\.py does not define the function down\(\)$',
    ):
        list(manager.get_steps(
            current=manager.get_latest_match(semver.NpmSpec('*')),
            target=semver.Version('0.0.0'),
        ))


@pytest.mark.parametrize(
    ['directory', 'error_class', 'error_match'],
    [
        (
            'bad-python-code',
            svip.errors.InvalidStepSource,
            (
                r'^bad Python code for .*/v3\.1__bad-python-code\.py: '
                r'Traceback \(most recent call last\):\n'
                r'  File ".*/v3\.1__bad-python-code\.py", line 5, in <module>\n'
                r'    x = 1 / 0\n'
                r'ZeroDivisionError: division by zero\n$'
            )
        ),
        (
            'up-not-defined',
            svip.errors.InvalidStepSource,
            r'^missing function up\(\) in .*/v3\.1__up-not-defined\.py$',
        ),
        (
            'invalid-metadata-type',
            svip.errors.InvalidStepSource,
            r'^metadata in .*/v3\.1__invalid-metadata-type.py must be a mapping \(e.g. a dict\)$',
        ),
        (
            'up-not-callable',
            svip.errors.InvalidStepSource,
            r'^variable "up" is not a callable in .*/v3\.1__up-not-callable\.py$'
        ),
        (
            'down-not-callable',
            svip.errors.InvalidStepSource,
            r'^variable "down" is not a callable in .*/v3\.1__down-not-callable\.py$'
        ),
        (
            'up-invalid-signature',
            svip.errors.InvalidStepSource,
            r'function up\(\) in .*/v3\.1__up-invalid-signature\.py contains an invalid signature$',
        ),
        (
            'down-invalid-signature',
            svip.errors.InvalidStepSource,
            r'function down\(\) in .*/v3\.1__down-invalid-signature\.py contains an invalid signature$',
        ),
    ],
)
def test_format_errors(directory, error_class, error_match, get_steps_dir_factory):
    manager = svip.migration.MigrationManager(
        get_steps_dir_factory(directory),
    )

    with pytest.raises(
        error_class,
        match=error_match,
    ):
        list(manager.get_steps(
            current=semver.Version('0.0.0'),
            target=manager.get_latest_match(semver.NpmSpec('*')),
        ))
