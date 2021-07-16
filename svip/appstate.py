"""
This module provides the class `AppStateBackend`, which is the abstract base
class that application state back ends (ASBs) must extend in order to provide
essential functionality for the migration process.
"""
import abc
import datetime
import contextlib
import typing as T

import semantic_version as semver

from . import migration


class AppStateBackup(abc.ABC):
    """
    This is an abstract base class to represent objects that are results of a
    successful backup of the application's state.

    An ASB that supports backups must provide a subclass of `AppStateBackup`
    and return an instance of such a class as a result of
    `AppStateBackend.backup()`.
    """

    def restore(self):
        """
        Restore this backup.

        This method must be overridden if the ASB allows to restore the backup.

        An exception must be raised when an error occurs while restoring the
        backup.
        """
        raise NotImplementedError()

    def info(self) -> str:
        """
        Return a human-readable string containing information about this
        backup.

        The returned string may contain line breaks.

        The default implementation returns the output of ``repr()`` called for
        this object.

        :returns: the string containing the info.
        """
        return repr(self)


class AppStateBackend(abc.ABC):
    """
    This is the abstract base class for application state back ends. The
    functionalities provided by back ends are described bellow:

    **Management of version state**
      This is a required functionality as it is essential for the migration
      process. The required methods for version state management are
      ``set_version()`` and ``get_version()``. Optionally, an implementation of
      ``get_version_history()`` can also be provided.

    **Backup and restoration of application data**
      The ability of performing backups allows SVIP to save a backup of the
      application state before starting a migration process. Back ends can
      provide backup functionality by overriding the ``backup()`` method.

      SVIP can also be instructed to restore the backup if an error occurs
      during the migration, such a functionality is provided by overriding the
      ``restore()`` method of the backup class used for the returned object.
      This is particularly useful when transactions are not supported by the
      back end.

      Although highly recommended, the implementation of such functionality is
      optional.

    **Transactions**
      When available, SVIP will try run the migration in a transaction, so that 
      changes to the state are only committed if all steps are successful. Back
      ends must override the ``transaction()`` method in order to support such
      a functionality.

      Although highly recommended when applicable, the implementation of such
      functionality is optional.
    """

    @abc.abstractmethod
    def set_version(self,
        current: semver.Version,
        target: semver.Version,
    ) -> T.Tuple[bool, semver.Version, semver.Version]:
        """
        Atomically update the current and target version of the schema.

        :param current: the new value for the current version.

        :param target: the new value for the target version.

        The current version is the version of the current schema of the
        application's state and the target version, if not None, is the target
        version of a migration process.

        The update must be atomic and, with ``current_before`` and
        ``target_before`` used to denote the values prior to the update, this
        method only perform the update if the following conditions hold:

        (1) either ``target_before is None`` or ``target is None`` (exclusive
          "or"):

            - When ``target_before is None`` and ``target is not None``, the
              transition marks the start of a migration process. For this case,
              this restriction means that no other migration process might be
              in execution when one is about start.

            - When ``target_before is not None`` and ``target is None``, the
              transition marks the end of a migration process.

              - If ``current_before != current``, the transition marks the end
                of a successful migration progress.

              - If ``current_before == current``, the transition marks the end
                of an unsuccessful migration progress.

        (2) ``current_before != current`` if, and only if, ``current =
            target_before`` and ``target is None``. This transition marks the
            end of a successful migration process.

        :returns: a 3-element tuple containing the following values: a boolean
          that tells whether the update was done; the value of
          ``current_before`` and the value of ``target_before``.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_version(self) -> T.Tuple[semver.Version, semver.Version]:
        """
        Atomically read the current and target version of the schema.

        :returns: a 2-element tuple containing the current and target versions,
          respectively.
        """
        raise NotImplementedError()

    def get_version_history(self) -> T.List[T.Tuple[semver.Version, datetime.datetime]]:
        """
        Return the history of updates in the schema version as a list.

        :returns: a list of 2-element tuples containing the schema version and
            the timestamp of the update. The list is sorted in chronological
            order.
        """
        raise NotImplementedError()

    def backup(self, info: migration.MigrationInfo) -> AppStateBackup:
        """
        Perform a backup of the application's state and return a
        `AppStateBackup` object.

        This method must raise an exception if the backup is not successful.

        ABSs that do not support backups do not need to override this method.

        :param info: object containing information about the migration process.

        :returns: an object representing the backup.
        """
        raise NotImplementedError()

    def transaction(self) -> contextlib.AbstractContextManager:
        """
        Return a context manager to represent a transaction.

        The returned context manager must only commit the changes made to the
        application state if it exits successfully, otherwise all the changes
        must be rolled back.

        ABSs that do not support transactions do not need to override this
        method.

        :returns: a context manager for the transaction.
        """
        raise NotImplementedError()

    def supports_backup(self) -> bool:
        """
        Return true if backup is supported by this back end and false
        otherwise.

        A back end is considered to support backup operations if the
        ``backup()``  method is overriden by the subclass.
        """
        return self.backup.__func__ != AppStateBackend.backup

    def supports_transaction(self) -> bool:
        """
        Return true if transaction is supported by this back end and false
        otherwise.

        A back end is considered to support transaction if the
        ``transaction()`` method is overriden by the subclass.
        """
        return self.transaction.__func__ != AppStateBackend.transaction
