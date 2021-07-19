"""
This module provides the class ``SVIP`` which models de central object to be
used for performing common operations of SVIP.
"""
import contextlib
import typing as T

import semantic_version as semver

from . import (
    appstate,
    errors,
    migration,
)


DEFAULT_MIGRATIONS_DIR = pathlib.Path('migrations')
"""
The default path used for `SVIPConf.migrations_dir`.
"""


class SVIPConf:
    """
    Configuration object for instances of `SVIP`.
    """

    def __init__(self,
            migrations_dir: pathlib.Path = DEFAULT_MIGRATIONS_DIR,
        ):
        """
        Initialize the configuration object.

        All arguments are stored as attributes of the object.

        :param migrations_dir: path to the directory where migration scripts
          are located.
        """
        self.migrations_dir = pathlib.Path(migrations_dir)


class SVIP:
    """
    The class ``SVIP`` provides the main funcionalities of this library.
    """

    def __init__(self,
            asb: appstate.AppStateBackend,
            conf: SVIPConf = SVIPConf()
        ):
        """
        Initialize the object.

        :param asb: the back end to be used for performing operations on the
          application's state during a migration. Those include getting and
          updating version information; generating and restoring backup; and
          encapsulating the migration process in a transaction.

        :param conf: the configuration object.
        """
        raise NotImplementedError()

    def current_version(self) -> semver.Version:
        """
        Read the current version of the schema and return it.
        """
        raise NotImplementedError()

    def check(self, spec: T.Union[str, semver.NpmSpec]):
        """
        Check if application code can use the application state now.

        This method does two types of checks: (i) it checks if there is no
        active migration in progress and (ii) if the current version of the
        schema is compatible with the version requirement given by `spec`. If
        any fails, an exception is raised.

        :param spec: an NPM-style version requirement specification. If a `str`
          is provided, it is converted to a `semantic_version.NpmSpec`.

        :raises MigrationInProgressError: if there is a migration in progress.

        :raises IncompatibleVersionError: if the current version of the schema
          is incompatible with `spec`.
        """
        raise NotImplementedError()

    def cli(self, argv: T.List[str] = None) -> int:
        """
        Provide a command line interface.

        This function can be used by the main routine of a program to provide
        a command line interface with subcommands exposing functionalities of
        SVIP.

        :param argv: the list of `str`s to be used as command line arguments.
          By default (i.e., if `None` is passed), it uses ``sys.argv[1:]``.

        :returns: the exit status of the CLI. This can be used as argument of
          ``exit()`` for providing the exit status of the main program.
        """
        raise NotImplementedError()

    def get_migrations_manager(self) -> migration.MigrationManager:
        """
        Return the object responsible for locating and loading migrations.
        """
        raise NotImplementedError()

    def migrate(self,
            target: T.Union[str, semver.Version],
            save_backup: bool = True,
            restore_backup: bool = None,
        ):
        """
        Perform the migration of the application state to a target schema
        version.

        This method gathers the sequence all migrations that must be executed
        in order to get the application's state to the target schema version
        and runs them in order.

        The migration process might be either an *upgrade*, when the target
        version is higher than the current one, or a *downgrade*, then the
        target version is lower than the current one. If the current version is
        the same as the target, then nothing is done.

        If the application state back end implements transactions, all
        migration steps are performed in the context of a transaction.

        If `save_backup` is true (the default), then a backup is created before
        starting the migration process. If an error occurs and `restore_backup`
        is true, this method attempts to restore the backup.

        The default value of `restore_backup` depends on whether the
        application state back end supports transactions, in which case the
        default value will be true and false otherwise. Note that this
        parameter is ignored if `save_backup` is false.

        :raises BackupFailedError: if an error occurred during the backup.

        :raises BackupNotImplementedError: if `use_backup` is true and the
          application state back end does not support making backups.

        :raises RestoreNotImplementedError: if `restore_backup` is true and the
        application state back end does not support restoring backups.

        :raises MigrationError: if an error occurred during the execution of
          migration steps.

        :raises RestoreFailedError: if an error occurred when restoring the
          backup after a failed migration. The original error is attached as
          the ``original_error`` attribute of the raised exception.

        """
        raise NotImplementedError()
