import pytest
import semantic_version as semver

import svip.migration


def test_dir_with_helper_module(filenames_dir_factory):
    manager = svip.migration.MigrationManager(
        filenames_dir_factory('with-helper-module'),
    )
    manager.get_latest_match(semver.NpmSpec('*'))
