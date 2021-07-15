import pytest
import semantic_version as semver

import svip.errors
import svip.migration


def test_upgrade(datadir):
    manager = svip.migration.MigrationManager(datadir / 'valid-step-filenames')

    versions = manager.get_versions(
        current=None,
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


def test_downgrade(datadir):
    manager = svip.migration.MigrationManager(datadir / 'valid-step-filenames')

    versions = manager.get_versions(
        current=semver.Version('0.1.2'),
        target=None,
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


def test_no_op(datadir):
    manager = svip.migration.MigrationManager(datadir / 'valid-step-filenames')

    versions = manager.get_versions(current=None, target=None)
    assert versions == []

    versions = manager.get_versions(
        current=semver.Version('0.0.2'),
        target=semver.Version('0.0.2'),
    )
    assert versions == []


def test_version_not_found(datadir):
    manager = svip.migration.MigrationManager(datadir / 'valid-step-filenames')

    with pytest.raises(svip.errors.VersionNotFoundError):
        manager.get_versions(current=semver.Version('3.4.1'), target=None)

    with pytest.raises(svip.errors.VersionNotFoundError):
        manager.get_versions(target=semver.Version('0.1.1'), current=None)

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
        manager.get_versions(current=None, target=semver.Version('1.0.0'))
