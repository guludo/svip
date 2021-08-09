"""
This module provides the class `CLI`, which provides a command line interface
for SVIP.
"""
from __future__ import annotations

import argparse
import collections.abc
import sys
import typing as T

import semantic_version as semver

from . import (
    cli_util,
    svip,
)


class CLI:
    """
    The CLI class provides a command line interface for SVIP. An instance of
    this class is returned by `SVIP.cli()`.

    The method `run()` provides the main functionality, which is parsing and
    executing a command.
    """

    SD = cli_util.SubcommandDecorator(name_prefix='__cmd_')

    def __init__(self, sv: 'svip.SVIP', prog: str = None):
        self.__sv = sv
        self.__create_parser(prog)

    def run(self,
            argv: T.List[str] = None,
            dryrun: bool = False,
        ) -> T.Union[int, dict]:
        """
        This function can be used by the main routine of a program to provide
        a command line interface with subcommands exposing functionalities of
        SVIP.

        :param argv: the list of `str`s to be used as command line arguments.
          By default (i.e., if `None` is passed), it uses ``sys.argv[1:]``.

        :param dryrun: parse `argv`, but do not make the call to run the
          command, but return a dictionary containing the function and
          arguments for the call. This parameter is primarily used for testing.

        :returns: if `dryrun` is false (the default), the returned value will
          be the exit status for the command. This can be used as argument of
          ``exit()`` for providing the exit status of the main program. If
          `dryrun` is true, then a dictionary if the call data is returned.
        """
        if argv is None:
            argv = sys.argv[1:] # pragma: no cover
        args = self.__parser.parse_args(argv)
        call_data = args.fn(self, args)
        call_data.setdefault('args', tuple())
        call_data.setdefault('kwargs', {})

        if dryrun:
            return call_data
        else:
            try:
                r = call_data['fn'](*call_data['args'], **call_data['kwargs'])
            except Exception as e:
                print(e, file=sys.stderr)
                return 1
            else:
                if isinstance(r, (collections.abc.Generator, list, tuple, set)):
                    for item in r:
                        print(item)
                elif r is not None:
                    print(r)
            return 0

    def __create_parser(self, prog: str = None):
        self.__parser = argparse.ArgumentParser(
            prog=prog or sys.argv[0],
        )
        subparsers = self.__parser.add_subparsers()
        self.SD.create_parsers(subparsers)

    @SD.add_argument(
        '--target',
        type=semver.Version,
    )
    @SD.add_argument(
        '--save-backup',
        action=cli_util.BoolAction,
        default=True,
    )
    @SD.add_argument(
        '--restore-backup',
        action=cli_util.BoolAction,
        default=None,
    )
    @SD.add_argument(
        '--allow-no-guardrails',
        action=cli_util.BoolAction,
        default=False,
    )
    @SD.add_argument(
        '--verbose',
        action=cli_util.BoolAction,
        default=True,
    )
    def __cmd_migrate(self, args):
        return {
            'fn': self.__sv.migrate,
            'kwargs': {
                'target': args.target,
                'save_backup': args.save_backup,
                'restore_backup': args.restore_backup,
                'allow_no_guardrails': args.allow_no_guardrails,
                'verbose': args.verbose,
            },
        }

    @SD.add_argument(
        '--spec',
        type=semver.NpmSpec,
    )
    def __cmd_match(self, args):
        return {
            'fn': self.__sv.get_migrations_manager().get_latest_match,
            'kwargs': {
                'spec': args.spec,
            },
        }

    @SD.add_argument(
        '--current',
        type=semver.Version,
        default=semver.Version('0.0.0'),
    )
    @SD.add_argument(
        '--target',
        type=semver.Version,
    )
    def __cmd_steps(self, args):
        manager = self.__sv.get_migrations_manager()
        if args.target is None:
            args.target = manager.get_latest_match(semver.NpmSpec('*'))
        return {
            'fn': self.__sv.get_migrations_manager().get_steps,
            'kwargs': {
                'current': args.current,
                'target': args.target,
            },
        }

    @SD.cmd()
    def __cmd_backup(self, args):
        return {
            'fn': self.__sv.backup,
            'kwargs': {
                'verbose': True,
            },
        }
