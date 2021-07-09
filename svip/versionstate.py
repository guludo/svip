"""
This module provides the class `VersionStateBackend`, which is the abstract
base class that version state back ends (VSBs) must extend in order provide the
essential functionality of managing state about the application's schema
version.
"""
import abc
import datetime
import typing as T


class VersionStateBackend(abc.ABC):
    """
    This is the abstract base class for version state back ends.
    """

    @abc.abstractmethod
    def set_version(self, current: semver.Version, target: semver.Version):
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

        (1) ``target_before != target`` and either ``target_before is None`` or
            ``target is None``.

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

    @abc.abstractmethod
    def get_history(self) -> T.List[T.Tuple[semver.Version, datetime.datetime]]:
        """
        Return the history of updates in the schema version as a list.

        :returns: a list of 2-element tuples containing the schema version and
            the timestamp of the update. The list is sorted in chronological
            order.
        """
        raise NotImplementedError()
