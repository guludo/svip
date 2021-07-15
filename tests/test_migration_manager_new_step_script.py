import shutil

import semantic_version as semver

import svip.migration


def test_script_content(valid_step_filenames_dir, tmp_path):
    shutil.copytree(
        valid_step_filenames_dir,
        tmp_path,
        dirs_exist_ok=True,
    )

    manager = svip.migration.MigrationManager(tmp_path)
    script_path, _ = manager.new_step_script(
        name='testing minor  bump',
        bump_type=svip.migration.BumpType.MINOR,
    )
    expected_content = '\n'.join([
        "\"\"\"",
        "Migration step for version 2.66.0 of the application's schema.",
        "\"\"\"",
        "",
        "",
        "def up():",
        "    # TODO: Implement this!",
        "    raise NotImplementedError()",
        "",
        "",
        "def down():",
        "    # TODO: Implement this if this step is reversible. Otherwise,",
        "    # remove the definition of down().",
        "    raise NotImplementedError()",
    ])
    assert script_path.read_text() == expected_content


def test_in_existing_dir(valid_step_filenames_dir, tmp_path):
    shutil.copytree(
        valid_step_filenames_dir,
        tmp_path,
        dirs_exist_ok=True,
    )

    manager = svip.migration.MigrationManager(tmp_path)

    latest_before_new_steps = manager.get_latest_match(semver.NpmSpec('*'))
    versions_before_new_steps = manager.get_versions(
        current=None,
        target=latest_before_new_steps,
    )

    script_path, version = manager.new_step_script(
        name='testing minor  bump',
        bump_type=svip.migration.BumpType.MINOR,
    )
    assert script_path == tmp_path / 'v2.66.0__testing-minor--bump.py'
    assert version == semver.Version('2.66.0')
    assert script_path.is_file()

    script_path, version = manager.new_step_script(
        name=' testing a major bump',
        bump_type=svip.migration.BumpType.MAJOR,
    )
    assert script_path == tmp_path / 'v3.0.0__-testing-a-major-bump.py'
    assert version == semver.Version('3.0.0')
    assert script_path.is_file()

    script_path, version = manager.new_step_script(
        name='and now a patch bump ',
        bump_type=svip.migration.BumpType.PATCH,
    )
    assert script_path == tmp_path / 'v3.0.1__and-now-a-patch-bump-.py'
    assert version == semver.Version('3.0.1')
    assert script_path.is_file()

    assert manager.get_latest_match(semver.NpmSpec('*')) == semver.Version('3.0.1')

    new_versions = manager.get_versions(
        current=None,
        target=semver.Version('3.0.1'),
    )
    expected_new_versions = versions_before_new_steps + [
        semver.Version('2.66.0'),
        semver.Version('3.0.0'),
        semver.Version('3.0.1'),
    ]
    assert new_versions == expected_new_versions


def test_in_empty_dir(tmp_path):
    manager = svip.migration.MigrationManager(tmp_path)

    script_path, version = manager.new_step_script(
        name='testing minor  bump',
        bump_type=svip.migration.BumpType.MINOR,
    )
    assert script_path == tmp_path / 'v0.1.0__testing-minor--bump.py'
    assert version == semver.Version('0.1.0')
    assert script_path.is_file()

    script_path, version = manager.new_step_script(
        name=' testing a major bump',
        bump_type=svip.migration.BumpType.MAJOR,
    )
    assert script_path == tmp_path / 'v1.0.0__-testing-a-major-bump.py'
    assert version == semver.Version('1.0.0')
    assert script_path.is_file()

    script_path, version = manager.new_step_script(
        name='and now a patch bump ',
        bump_type=svip.migration.BumpType.PATCH,
    )
    assert script_path == tmp_path / 'v1.0.1__and-now-a-patch-bump-.py'
    assert version == semver.Version('1.0.1')
    assert script_path.is_file()
