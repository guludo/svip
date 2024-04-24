# SPDX-License-Identifier: MPL-2.0
import pytest
import semantic_version as semver

import svip
import svip.migration


def test_upgrade(filenames_dir_factory):
    manager = svip.migration.MigrationManager(filenames_dir_factory())

    versions = manager.get_versions(
        current=semver.Version('0.0.0'),
        target=semver.Version('2.65.921'),
    )
    expected_versions = [
        semver.Version('0.0.1'),
        semver.Version('0.0.2'),
        semver.Version('0.1.0'),
        semver.Version('0.1.2'),
        semver.Version('0.1.15'),
        semver.Version('2.65.921'),
    ]
    assert versions == expected_versions

    versions = manager.get_versions(
        current=semver.Version('0.1.0'),
        target=semver.Version('0.1.15'),
    )
    expected_versions = [
        semver.Version('0.1.2'),
        semver.Version('0.1.15'),
    ]
    assert versions == expected_versions


def test_downgrade(filenames_dir_factory):
    manager = svip.migration.MigrationManager(filenames_dir_factory())

    versions = manager.get_versions(
        current=semver.Version('0.1.2'),
        target=semver.Version('0.0.0'),
    )
    expected_versions = [
        semver.Version('0.1.2'),
        semver.Version('0.1.0'),
        semver.Version('0.0.2'),
        semver.Version('0.0.1'),
    ]
    assert versions == expected_versions

    versions = manager.get_versions(
        current=semver.Version('0.1.15'),
        target=semver.Version('0.0.2'),
    )
    expected_versions = [
        semver.Version('0.1.15'),
        semver.Version('0.1.2'),
        semver.Version('0.1.0'),
    ]
    assert versions == expected_versions


def test_no_op(filenames_dir_factory):
    manager = svip.migration.MigrationManager(filenames_dir_factory())

    versions = manager.get_versions(
        current=semver.Version('0.0.0'),
        target=semver.Version('0.0.0'),
    )
    assert versions == []

    versions = manager.get_versions(
        current=semver.Version('0.0.2'),
        target=semver.Version('0.0.2'),
    )
    assert versions == []


def test_version_not_found(filenames_dir_factory):
    manager = svip.migration.MigrationManager(filenames_dir_factory())

    with pytest.raises(svip.errors.VersionNotFoundError):
        manager.get_versions(
            current=semver.Version('3.4.1'),
            target=semver.Version('0.0.0'),
        )

    with pytest.raises(svip.errors.VersionNotFoundError):
        manager.get_versions(
            current=semver.Version('0.0.0'),
            target=semver.Version('0.1.1'),
        )

    with pytest.raises(svip.errors.VersionNotFoundError):
        # An exception must be raised even if current and target are the same
        manager.get_versions(
            current=semver.Version('15.0.0'),
            target=semver.Version('15.0.0'),
        )


def test_empty_dir(tmp_path):
    manager = svip.migration.MigrationManager(tmp_path)
    with pytest.raises(svip.errors.VersionNotFoundError):
        # Testing with any version here. Just to make sure manager reads the
        # empty directory
        manager.get_versions(
            current=semver.Version('0.0.0'),
            target=semver.Version('1.0.0'),
        )


def test_partial_version_strings(filenames_dir_factory, datadir):
    manager = svip.migration.MigrationManager(
        filenames_dir_factory('partial-versions', inherit_from=None)
    )
    versions = manager.get_versions(
        current=semver.Version('0.0.0'),
        target=manager.get_latest_match(semver.NpmSpec('*')),
    )
    expected_versions = [
        semver.Version('1.0.0'),
        semver.Version('2.0.0'),
        semver.Version('2.1.0'),
    ]
    assert versions == expected_versions
