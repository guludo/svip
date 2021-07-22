"""
This module provides the class `SVIP`, which models de central object to be
used for performing common operations of SVIP.
"""
import contextlib
import pathlib
import traceback
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
            conf: SVIPConf = SVIPConf(),
            ctx: T.Any = None,
        ):
        """
        Initialize the object.

        :param asb: the back end to be used for performing operations on the
          application's state during a migration. Those include getting and
          updating version information; generating and restoring backup; and
          encapsulating the migration process in a transaction.

        :param conf: the configuration object.

        :param ctx: value that will be passed down to the migration manager.
          This can be used to share data or resources that will be used by the
          migration steps (e.g. a database connection).
        """
        self.__asb = asb
        self.__conf = conf
        self.__manager = migration.MigrationManager(
            path=self.__conf.migrations_dir,
            ctx=ctx,
        )

    def current_version(self) -> semver.Version:
        """
        Read the current version of the schema and return it.
        """
        current, _ = self.__asb.get_version()
        return current

    def check(self, spec: T.Union[str, semver.NpmSpec]):
        """
        Check if application code can use the application state now.

        :param spec: an NPM-style version requirement specification. If a `str`
          is provided, it is converted to a `semantic_version.NpmSpec`.

        This method does the following checks:

        (i) if the application state is in a consistent state;

        (ii) if there is no active migration in progress;

        (iii) if the current version of the schema is compatible with the
          version requirement given by `spec`.

        If any check fails, an exception is raised.

        :raises InconsistentStateError: if the application state is marked as
          inconsistent.

        :raises MigrationInProgressError: if there is a migration in progress.

        :raises IncompatibleVersionError: if the current version of the schema
          is incompatible with `spec`.
        """
        inconsistency = self.__asb.get_inconsistency()
        if inconsistency:
            msg = 'application state is marked as inconsistent'
            raise errors.InconsistentStateError()

        current, target = self.__asb.get_version()
        if target is not None:
            msg = f'there is a migration in progress for version {target}'
            raise errors.MigrationInProgressError(msg)

        if isinstance(spec, str):
            spec = semver.NpmSpec(spec)

        if not spec.match(current):
            msg = f'version spec {spec} is incompatible with current schema version {current}'
            raise errors.IncompatibleVersionError(msg)

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
        return self.__manager

    def migrate(self,
            target: T.Union[str, semver.Version],
            save_backup: bool = True,
            restore_backup: bool = None,
            allow_no_guardrails: bool = False,
        ):
        """
        Perform the migration of the application state to a target schema
        version indicated by `target`.

        The value `target` of target can be either a `semantic_version.Version`
        object or a string. In the case of the latter, the string will be
        converted to a `semantic_version.Version` object.

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
        default value will be false and true otherwise. Note that this
        parameter is ignored if `save_backup` is false.

        If ``save_backup`` is false and the application state back end does not
        implement transactions, then this method refused to continue unless
        `allow_no_guardrails`` is true (which is false by default).

        This method raises an error in case of a failure. The following
        exceptions might be raised:

        :raises BackupFailedError: if an error occurred during the backup.

        :raises BackupNotImplementedError: if `use_backup` is true and the
          application state back end does not support making backups.

        :raises RestoreNotImplementedError: if `restore_backup` is true and the
          application state back end does not support restoring backups.

        :raises NoGuardrailsError: if `save_backup` and transactions are not
          supported and the caller did not explicitly told us to allow that
          (i.e. `allow_no_guardrails` is false).

        :raises InconsistentStateError: if the application state is marked as
          inconsistent, which could be caused by an earlier failed migration.

        :raises MigrationInProgressError: if there is a migration in progress
          at the time of the call.

        :raises MigrationError: if an error occurred during the execution of
          migration steps.

        :raises RestoreFailedError: if an error occurred when restoring the
          backup or the original version information after a failed migration.
          The original error is attached as the ``original_error`` attribute of
          the raised exception.

        :raises BackupFailedError: if an error occurred while creating the
          backup.

        :raises TransactionFailedError: if an error occurred when creating the
          transaction.
        """
        if isinstance(target, str):
            target = semver.Version(target)

        # Some preflight checks
        if save_backup and not self.__asb.supports_backup():
            msg = 'the application state back end does not support backup operations'
            raise errors.BackupNotImplementedError(msg)

        if (
            not save_backup and not self.__asb.supports_transaction() and
            not allow_no_guardrails
        ):
            msg = 'refusing to continue: migration would run with no backup and no transaction'
            raise errors.NoGuardrailsError(msg)

        if restore_backup is None:
            restore_backup = not self.__asb.supports_transaction()

        if restore_backup and not self.__asb.backup_supports_restore():
            msg = 'the application state back end does not support restoring backups'
            raise errors.RestoreNotImplementedError(msg)

        inconsistency = self.__asb.get_inconsistency()
        if inconsistency:
            msg = 'refusing to continue: application state is marked as inconsistent'
            raise errors.InconsistentStateError(msg)

        current, _ = self.__asb.get_version()

        if current == target:
            return

        is_upgrade = current < target
        steps = self.__manager.get_steps(current=current, target=target)

        # Mark the start of a migration process.
        try:
            updated, current_before, target_before = self.__asb.set_version(
                current=current,
                target=target,
            )
        except Exception as e:
            msg = f'failed to update version state before migration: {e}'
            raise RuntimeError(msg) from e
        else:
            if not updated:
                if target_before is not None:
                    msg = f'there is a migration in progress for version {target_before}'
                    raise errors.MigrationInProgressError(msg)
                else:
                    msg = 'failed to update version state before migration: unknown reason'
                    raise RuntimeError(msg)

        # At this point we have officially started the migration process.
        migration_info = migration.MigrationInfo(
            current=current,
            target=target,
        )

        def restore_version(original_error):
            try:
                restored, _, _ = self.__asb.set_version(
                    current=current,
                    target=None,
                )
                if not restored:
                    raise Exception('unknown reason')
            except Exception as e:
                msg = f'failed to restore version after migration error: {e}'
                msg += f'\nmigration error: {original_error}'
                raise errors.RestoreFailedError(msg, original_error) from e

        # Save a backup if applicable.
        if save_backup:
            try:
                backup = self.__asb.backup(migration_info)
            except Exception as e:
                backup = None
                msg = f'failed to perform backup: {e}'
                error = errors.BackupFailedError(msg)
                try:
                    restore_version(error)
                except Exception as restore_version_error:
                    self.__asb.register_inconsistency(
                        str(restore_version_error),
                        None,
                    )
                    raise
                raise error

        # Create the transaction if applicable.
        try:
            if self.__asb.supports_transaction():
                transaction = self.__asb.transaction()
            else:
                transaction = contextlib.nullcontext()
        except Exception as e:
            msg = f'failed to start transaction: {e}'
            error = errors.TransactionFailedError(msg)
            try:
                restore_version(error)
            except Exception as restore_version_error:
                self.__asb.register_inconsistency(
                    str(restore_version_error),
                    backup.info() if backup else None,
                )
                raise
            raise error

        # Run the migration!
        try:
            with transaction:
                for step in steps:
                    try:
                        if is_upgrade:
                            step.up()
                        else:
                            step.down()
                    except Exception as e:
                        formatted_error = traceback.format_exc(limit=-1)
                        if is_upgrade:
                            msg = f'error running upgrade step to {step.version}: {formatted_error}'
                        else:
                            msg = f'error running downgrade step from {step.version}: {formatted_error}'
                        raise Exception(msg) from e

                # Now that all migration steps are executed, let's update
                # the version information in the application state.
                try:
                    updated, _, _ = self.__asb.set_version(
                        current=target,
                        target=None,
                    )
                    if not updated:
                        raise Exception('unknown reason')
                except Exception as e:
                    msg = f'failed to update version information after execution of migration steps: {e}'
                    raise Exception(msg) from e
        except Exception as e:
            msg = f'failed to run migration: {e}'
            migration_error = errors.MigrationError(msg)

            # Try to somehow restore application state, if not possible
            # mark state as inconsistent
            try:
                if self.__asb.supports_transaction() and transaction.rollback_successful():
                    restore_version(migration_error)
                elif save_backup and restore_backup and backup:
                    try:
                        backup.restore()
                    except Exception as e:
                        msg = f'failed to restore backup after migration failure: {e}'
                        msg += f'\nmigration error: {migration_error}'
                        raise errors.RestoreFailedError(msg, migration_error) from e
                else:
                    # Well, if we have no means of restoring application state,
                    # then let's just raise the original error and let the
                    # "except clause" take care of marking the application
                    # state as inconsistent.
                    raise migration_error
            except Exception as e:
                # We were not able to restore application state. Let's mark it
                # as inconsistent and re-raise the error.
                self.__asb.register_inconsistency(
                    str(e),
                    backup.info() if backup else None,
                )
                raise
            else:
                # If we got here, at least we were able to restore the
                # application state. Let's just raise the original error.
                raise migration_error
        # Phew! If we got here, the migration process was a success :-)
