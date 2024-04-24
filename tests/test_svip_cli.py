# SPDX-License-Identifier: MPL-2.0
import contextlib
import io
import pathlib

import pytest
import semantic_version as semver

import svip

def test_exit_status(svip_factory):
    sv, appstate = svip_factory()
    cli = sv.cli()

    # Existing version
    assert cli.run(argv=['migrate', '--target', '0.1.15']) == 0

    # Non-existing version
    assert cli.run(argv=['migrate', '--target', '4.0.0']) == 1


def test_print_returned_value(svip_factory):
    sv, appstate = svip_factory()
    cli = sv.cli()

    with contextlib.redirect_stdout(io.StringIO()) as f:
        cli.run(argv=['match', '--spec', '^0.1.0'])

    assert f.getvalue() == '0.1.15\n'


def test_print_generator_returned_value(svip_factory):
    sv, appstate = svip_factory()
    cli = sv.cli()

    with contextlib.redirect_stdout(io.StringIO()) as f:
        cli.run(
            argv=['steps', '--current', '0.0.1', '--target', '0.1.15'],
        )

    # The command "steps" is expected to return a path at each line. Since the
    # path is based on a temporary directory, let's just extract the names of
    # each file.
    names = [pathlib.Path(line).name for line in f.getvalue().splitlines()]
    expected_names = [
        'v0.0.2__this-is-the-second-step.py',
        'v0.1.0__this-is-the-first-bump-on-minor.py',
        'v0.1.2__this-must-be-before-0.1.15.py',
        'v0.1.15__bumps-higher-than-one-are-okay.py',
    ]
    assert names == expected_names


@pytest.mark.parametrize('argv,expected_call_data', [
    (
        ['migrate',
            '--target', '2.0.1',
            '--save-backup',
            '--no-restore-backup',
            '--allow-no-guardrails',
        ],
        {
            'fn': lambda sv: sv.migrate,
            'args': tuple(),
            'kwargs': {
                'target': semver.Version('2.0.1'),
                'save_backup': True,
                'restore_backup': False,
                'allow_no_guardrails': True,
                'verbose': True,
            },
        },
    ),
    (
        ['match', '--spec', '^2.0'],
        {
            'fn': lambda sv: sv.get_migrations_manager().get_latest_match,
            'args': tuple(),
            'kwargs': {
                'spec': semver.NpmSpec('^2.0'),
            },
        },
    ),
    (
        ['steps'],
        {
            'fn': lambda sv: sv.get_migrations_manager().get_steps,
            'args': tuple(),
            'kwargs': {
                'current': semver.Version('0.0.0'),
                'target': semver.Version('2.65.921'),
            },
        },
    ),
    (
        ['steps', '--current', '0.0.1', '--target', '0.1.15'],
        {
            'fn': lambda sv: sv.get_migrations_manager().get_steps,
            'args': tuple(),
            'kwargs': {
                'current': semver.Version('0.0.1'),
                'target': semver.Version('0.1.15'),
            },
        },
    ),
    (
        ['backup'],
        {
            'fn': lambda sv: sv.backup,
            'args': tuple(),
            'kwargs': {
                'verbose': True,
            },
        }
    ),
])
def test_dryruns(svip_factory, argv, expected_call_data):
    sv, appstate = svip_factory()
    cli = sv.cli()

    expected_call_data = dict(expected_call_data)
    expected_call_data['fn'] = expected_call_data['fn'](sv)

    call_data = cli.run(argv=argv, dryrun=True)

    assert call_data == expected_call_data
