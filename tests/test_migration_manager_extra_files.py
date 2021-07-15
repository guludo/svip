import pytest
import semantic_version as semver

import svip.errors
import svip.migration


def test_dir_with_helper_module(datadir):
    manager = svip.migration.MigrationManager(datadir / 'with-helper-module')
    manager.get_latest_match(semver.NpmSpec('*'))


def test_dir_with_unrecognized_script(datadir):
    manager = svip.migration.MigrationManager(datadir / 'with-unrecognized-script')
    with pytest.raises(svip.errors.UnrecognizedScriptFound):
        manager.get_latest_match(semver.NpmSpec('*'))
