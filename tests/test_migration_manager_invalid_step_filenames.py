import pathlib

import pytest
import semantic_version as semver

import svip.errors
import svip.migration


@pytest.fixture
def datadir():
    return pathlib.Path(__file__).parent / 'data'


def test_duplicated_versions(datadir):
    manager = svip.migration.MigrationManager(datadir / 'duplicated-versions')
    with pytest.raises(
        ValueError,
        match=r'.*v0\.1\.15.* and .*v0\.1\.15.* are defined as migration steps for the same target version$'
    ):
        manager.get_versions(
            current=None,
            target=semver.Version('2.65.921'),
        )


def test_invalid_version_string(datadir):
    manager = svip.migration.MigrationManager(datadir / 'invalid-version-string')
    with pytest.raises(
        ValueError,
        match=r'^.*v0\.foo\.0__step-with-invalid-version-string\.py contains an invalid version string: .*$',
    ):
        manager.get_versions(
            current=None,
            target=semver.Version('2.65.921'),
        )
