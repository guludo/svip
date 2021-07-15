import pytest
import semantic_version as semver

import svip.errors
import svip.migration


def test_not_found(datadir):
    manager = svip.migration.MigrationManager(datadir / 'valid-step-filenames')

    with pytest.raises(svip.errors.VersionNotFoundError):
        manager.get_latest_match(semver.NpmSpec('^1.1.0'))

    matched = manager.get_latest_match(semver.NpmSpec('^2.0.0'))
    assert matched == semver.Version('2.65.921')

    matched = manager.get_latest_match(semver.NpmSpec('~0.1.2'))
    assert matched == semver.Version('0.1.15')
