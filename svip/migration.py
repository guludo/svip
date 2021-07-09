"""
This module provides classes related to the migration process.

`MigrationStep`
    This class represents an object that makes the changes in the application
    state in order to get the schema from one version to the next (or
    previous).

`MigrationManager`
    Class responsible for locating and managing migration steps.

`MigrationInfo`
    A `MigrationInfo` object contains information about a migration process.
"""
from collections.abc import Iterable
import abc
import enum
import pathlib
import typing as T

import semantic_version as semver


class MigrationStep(abc.ABC):
    """
    Abstract base class responsible for migration steps. Subclasses implement
    the code necessary for changing the state and schema of the application in
    order to make the from the current schema version to the next or previous
    one.

    A migration step must implement an upgrade operation by overriding the
    ``up()`` method; and may also support a downgrade by overriding the
    ``down()`` method.
    """

    @abc.abstractmethod
    def up(self):
        """
        Change the application schema and state to the next version (i.e., the
        version this step is for).

        An exception must be raised in case the upgrade is unsuccessful.
        """
        raise NotImplementedError()

    def down(self):
        """
        Change the application schema and state to the previous version.

        An exception must be raised in case the upgrade is unsuccessful.

        This method must not be overridden if this step does not support a
        downgrade operation.
        """
        raise NotImplementedError()


BumpType = enum.Enum('BumpType', ['MAJOR', 'MINOR', 'PATCH'])
"""
Type of increment to be used when creating a new version from another one.
"""


class MigrationManager:
    """
    A `MigrationManager` is responsible for locating and managing migration
    steps.
    """

    def __init__(self, path: pathlib.Path):
        """
        Initialize this object.

        :param path: path to the directory containing migration step scripts.
        """
        raise NotImplementedError()

    def new_step_script(self,
            name: str,
            bump_type: BumpType,
        ) -> T.Tuple[pathlib.Path, semver.Version]:
        """
        Create a new migration step script.

        :param name: the name for this migration step.

        :param bump_type: this parameter defines which component of the latest
          version will be incremented for the definition of the new version.

        :returns: a 2-element tuple with the first element being the path of
          the created script and the second, the value of the new version.

        The created script will be created for the next version after the
        latest version found in the directory of migration step scripts. The
        next version is defined as the latest version incremented by one on one
        of the version components (major, minor or patch).
        """
        raise NotImplementedError()

    def get_latest_match(self, spec: semver.NpmSpec) -> semver.Version:
        """
        Return the latest version that satisfies the requirement defined by
        `spec`.

        :param spec: the NPM-style version requirement specification used for
          the match.

        :raises VersionNotFoundError: if no matching version was found.

        :returns: the matched version object.
        """
        raise NotImplementedError()

    def get_versions(self,
            current: semver.Version,
            target: semver.Version,
        ) -> Iterable[semver.Version]:
        """
        Find the sequences of versions between `current` (exclusive) and
        `target` (inclusive).

        :param current: the starting point (exclusive).

        :param target: the ending point (inclusive).

        :raises VersionNotFoundError: if there is no migration step for either
          `current` or `target`.

        :returns: an iterable of the sequence of version objects

        This method is useful for knowing the sequence of versions for which
        there must be migration steps in order to migration the schema version
        from `current` to `target`. The sequence will be in increasing order if
        ``current < target` and in decreasing order otherwise.

        Note that a ``None`` value for a version represents the very first
        state of the application.
        """
        raise NotImplementedError()

    def get_steps(self,
            current: semver.Version,
            target: semver.Version,
        ) -> Iterable[MigrationStep]:
        """
        Generate the sequence of `MigrationStep` objects that must be executed
        in order to get the application schema version from version `current`
        to `target`.

        :param current: the starting point of the migration.

        :param target: the ending point of the migration.

        :raises VersionNotFoundError: if either `current` or `target` is not
          found to be a valid version.

        :raises IrreversibleStepError: if the migration is a downgrade and
          one of the steps found does not support a downgrade operation.

        :returns: an iterable containing the sequence of migration steps
          necessary for the migration.
        """
        raise NotImplementedError()


class MigrationInfo:
    """
    A `MigrationInfo` object stores information about a migration process.
    """

    def __init__(self, current: semver.Version, target: semver.Version):
        """
        Initialize the object.

        All arguments are stored as attributes of the object with the same name
        of the parameter.

        :param current: the current version of the schema prior to the
          migration process.

        :param target: the next version of the schema in case the migration is
          successful.
        """
        self.current = current
        self.target = target
