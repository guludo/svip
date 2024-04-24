# SPDX-License-Identifier: MPL-2.0
import pytest
import semantic_version as semver

import svip
import svip.migration

@pytest.mark.parametrize(
    ['directory', 'error_class', 'error_match'],
    [
        (
            'duplicated-versions',
            ValueError,
            r'.*v0\.1\.15.* and .*v0\.1\.15.* are defined as migration steps for the same target version$',
        ),
        (
            'invalid-version-string',
            ValueError,
            r'^.*v0\.foo\.0__step-with-invalid-version-string\.py contains an invalid version string: .*$',
        ),
        (
            'with-v0.0.0',
            ValueError,
            r'.*: version 0\.0\.0 not allowed in migration steps$',
        ),
        (
            'with-unrecognized-script',
            svip.errors.UnrecognizedScriptFound,
            r'^found the following unrecognized scripts in .*: \{PosixPath\(\'.*/v4\.0\.0--invalid-for-using-hyphens-instead-of-underscores-after-version-string\.py\'\)\}$'
        ),
    ],
)
def test_invalid_step_filenames(filenames_dir_factory, directory, error_class, error_match):
    manager = svip.migration.MigrationManager(filenames_dir_factory(directory))
    with pytest.raises(
        error_class,
        match=error_match,
    ):
        manager.get_latest_match(semver.NpmSpec('*'))
