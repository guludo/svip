import pytest
import semantic_version as semver

import svip.errors
import svip.migration


@pytest.fixture
def steps_dir(datadir, merge_steps_dirs):
    """
    Generate the directory with merged steps.
    """
    def factory(srcdir=None):
        return merge_steps_dirs(
            datadir / 'get_steps' / 'base-files',
            (datadir / 'get_steps' / srcdir) if srcdir else None,
        )
    return factory


def test_valid_formats(steps_dir):
    manager = svip.migration.MigrationManager(steps_dir())

    steps = manager.get_steps(
        current=None,
        target=manager.get_latest_match(semver.NpmSpec('*')),
    )
    ids_from_metadata = [step.metadata['id_for_test'] for step in steps]
    expected_ids = ['v1', 'v2', 'v3', 'v4', 'v5']
    assert ids_from_metadata == expected_ids


def test_irreversible_step(steps_dir):
    manager = svip.migration.MigrationManager(steps_dir('irreversible-step'))

    with pytest.raises(
        svip.errors.IrreversibleStepError,
        match=r'^downgrade is not possible because .*/v3\.1__irreversible-step\.py does not define the function down\(\)$',
    ):
        list(manager.get_steps(
            current=manager.get_latest_match(semver.NpmSpec('*')),
            target=None,
        ))


@pytest.mark.parametrize(
    ['directory', 'error_class', 'error_match'],
    [
        (
            'bad-python-code',
            svip.errors.InvalidStepSource,
            r'^bad Python code for .*/v3\.1__.*$',
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
    ],
)
def test_format_errors(directory, error_class, error_match, steps_dir):
    manager = svip.migration.MigrationManager(steps_dir(directory))

    with pytest.raises(
        error_class,
        match=error_match,
    ):
        list(manager.get_steps(
            current=None,
            target=manager.get_latest_match(semver.NpmSpec('*')),
        ))
