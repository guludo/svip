"""
This module provides the class `AppStateBackend`, which is the abstract base
class that application state back ends (ASBs) must extend in order to provide
auxiliary functionality for the migration process.
"""
import abc
import contextlib


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
    functionalities provided by back ends are described bellow. A back end is
    not required to provide all of them.

    **Backup and restoration of application data**
      The ability of performing backups allows SVIP to save a backup of the
      application state before starting a migration process. Back ends can
      provide backup functionality by overriding the ``backup()`` method.

      SVIP can also be instructed to restore the backup if an error occurs
      during the migration, such a functionality is provided by overriding the
      ``restore()`` method of the backup class used for the returned object.
      This is particularly useful
      when transactions are not supported by the back end.

    **Transactions**
      When available, SVIP will try run the migration in a transaction, so that 
      changes to the state are only committed if all steps are successful. Back
      ends must override the ``transaction()`` method in order to support such
      a functionality.
    """

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
