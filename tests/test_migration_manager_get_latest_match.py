import pytest
import semantic_version as semver

import svip
import svip.migration


def test_not_found(filenames_dir_factory):
    manager = svip.migration.MigrationManager(filenames_dir_factory())

    with pytest.raises(svip.errors.VersionNotFoundError):
        manager.get_latest_match(semver.NpmSpec('^1.1.0'))

    matched = manager.get_latest_match(semver.NpmSpec('^2.0.0'))
    assert matched == semver.Version('2.65.921')

    matched = manager.get_latest_match(semver.NpmSpec('~0.1.2'))
    assert matched == semver.Version('0.1.15')
