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
import collections.abc
import enum
import inspect
import pathlib
import typing as T

import semantic_version as semver

from . import errors


V0 = semver.Version('0.0.0')


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
    def __init__(self):
        self.metadata = {}
        """
        Metadata about this migration step.
        """

        self.version = None
        """
        Version for which this step is.
        """

        self.ctx = None
        """
        Context variable, this can be used so that data and resources might be
        passed down by the main stript to migration steps.
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

    def __init__(self, path: pathlib.Path, ctx: T.Any = None):
        """
        Initialize this object.

        :param path: path to the directory containing migration step scripts.
        :param ctx: variable to be passed down to the ``ctx`` property of
          migration steps.
        """
        self.__path = path

        # Data that is filled with ``__read_migrations_dir()``. Any method that
        # needs to access this must call ``__read_migrations_dir()``.
        self.__version_indices = None
        self.__versions = None
        self.__steps_paths = None
        self.__ctx = ctx

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
        self.__read_migrations_dir()

        v = self.__versions[-1] if self.__versions else V0

        if bump_type == BumpType.MAJOR:
            next_version = v.next_major()
        elif bump_type == BumpType.MINOR:
            next_version = v.next_minor()
        elif bump_type == BumpType.PATCH:
            next_version = v.next_patch()
        else:
            raise RuntimeError(f'unhandled bump type: {bump_type}') # pragma: no cover

        template = '\n'.join([
            "\"\"\"",
            "Migration step for version {version} of the application's schema.",
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
        script_content = template.format(version=next_version)

        formatted_name = name.replace(' ', '-')
        script_filename = f'v{next_version}__{formatted_name}.py'
        script_path = self.__path / script_filename

        script_path.write_text(script_content)

        self.__version_indices[next_version] = len(self.__versions)
        self.__versions.append(next_version)
        self.__steps_paths.append(script_path)

        return script_path, next_version

    def get_latest_match(self, spec: semver.NpmSpec) -> semver.Version:
        """
        Return the latest version that satisfies the requirement defined by
        `spec`.

        :param spec: the NPM-style version requirement specification used for
          the match.

        :raises VersionNotFoundError: if no matching version was found.

        :returns: the matched version object.
        """
        self.__read_migrations_dir()
        for v in reversed(self.__versions):
            if spec.match(v):
                return v
        else:
            msg = f'no migration step found for spec {spec}'
            raise errors.VersionNotFoundError(msg)

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

        Note that ``semantic_version.Version('0.0.0')`` as value for a version
        represents the very first state of the application.
        """
        self.__read_migrations_dir()

        if current != V0 and current not in self.__version_indices:
            msg = f'no migration step found for {current}'
            raise errors.VersionNotFoundError(msg)

        if target != V0 and target not in self.__version_indices:
            msg = f'no migration step found for {target}'
            raise errors.VersionNotFoundError(msg)

        if current == target:
            return []

        if current < target:
            a = current
            b = target
            is_upgrade = True
        else:
            a = target
            b = current
            is_upgrade = False

        slice_start = 0 if a == V0 else (self.__version_indices[a] + 1)
        slice_end = self.__version_indices[b] + 1
        sliced_versions = self.__versions[slice_start:slice_end]
        r = sliced_versions if is_upgrade else reversed(sliced_versions)
        return list(r)

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

        :raises InvalidStepSource: if there is a problem with the source code
          of the script for a migration step

        :returns: an iterable containing the sequence of migration steps
          necessary for the migration.
        """
        versions = self.get_versions(current=current, target=target)

        # For each version, load the python code, create a subclass of
        # MigrationStep and instantiate it
        for version in versions:
            i = self.__version_indices[version]

            # Load the script
            step_path = self.__steps_paths[i]
            step_code = step_path.read_text()
            step_globals = {}
            try:
                exec(step_code, step_globals)
            except Exception as e:
                raise errors.InvalidStepSource(f'bad Python code for {step_path}: {e}')

            # Create the subclass of MigrationStep
            class_name = step_path.stem
            class_bases = (MigrationStep,)
            class_dict = {}

            if 'up' not in step_globals:
                raise errors.InvalidStepSource(f'missing function up() in {step_path}')
            else:
                try:
                    sig = inspect.signature(step_globals['up'])
                except TypeError:
                    msg = f'variable "up" is not a callable in {step_path}'
                    raise errors.InvalidStepSource(msg)

                if len(sig.parameters) == 1:
                    def up(self):
                        return step_globals['up'](self)
                elif len(sig.parameters) == 0:
                    def up(self):
                        return step_globals['up']()
                else:
                    msg = f'function up() in {step_path} contains an invalid signature'
                    raise errors.InvalidStepSource(msg)

                class_dict['up'] = up

            if 'down' in step_globals:
                try:
                    sig = inspect.signature(step_globals['down'])
                except TypeError:
                    msg = f'variable "down" is not a callable in {step_path}'
                    raise errors.InvalidStepSource(msg)

                if len(sig.parameters) == 1:
                    def down(self):
                        return step_globals['down'](self)
                elif len(sig.parameters) == 0:
                    def down(self):
                        return step_globals['down']()
                else:
                    msg = f'function down() in {step_path} contains an invalid signature'
                    raise errors.InvalidStepSource(msg)

                class_dict['down'] = down
            elif target < current:
                msg = f'downgrade is not possible because {step_path} does not define the function down()'
                raise errors.IrreversibleStepError(msg)

            cls = type(class_name, class_bases, class_dict)

            # Instantiate the step and initialize
            step = cls()

            step.version = version
            step.ctx = self.__ctx

            if 'metadata' in step_globals:
                metadata = step_globals['metadata']
                if not isinstance(metadata, collections.abc.Mapping):
                    msg = f'metadata in {step_path} must be a mapping (e.g. a dict)'
                    raise errors.InvalidStepSource(msg)
                step.metadata.update(metadata)

            yield step

    def __read_migrations_dir(self):
        """
        Read the directory with migration steps and fill appropriate instance
        variables.

        This method reads the directory only once. Any subsequent call is
        ignored.
        """
        if self.__version_indices is not None:
            return

        paths = list(self.__path.glob('v*__*.py'))

        # Let's check if there are other scripts in there. A migration step not
        # being recognized because typo is dangerous for data integrity.
        # TODO: document the possibility of having helper modules prefixed with
        # 'mod_'.
        all_paths = set(self.__path.glob('*.py'))
        mod_paths = set(self.__path.glob('mod_*.py'))
        unrecognized_paths = all_paths - mod_paths - set(paths)
        if unrecognized_paths:
            msg = f'found the following unrecognized scripts in {self.__path}: {unrecognized_paths}'
            raise errors.UnrecognizedScriptFound(msg)

        versions = [None] * len(paths)
        for i, path in enumerate(paths):
            version_str = path.name[1:path.name.index('__')]
            try:
                parsed = semver.Version.parse(version_str, partial=True)
                version = semver.Version(
                    major=parsed[0] or 0,
                    minor=parsed[1] or 0,
                    patch=parsed[2] or 0,
                    prerelease=parsed[3],
                    build=parsed[4],
                )
                if version == V0:
                    raise ValueError('version 0.0.0 not allowed in migration steps')
            except ValueError as e:
                msg = f'{path} contains an invalid version string: {e}'
                raise ValueError(msg) from e
            else:
                versions[i] = version

        if paths:
            versions, paths = zip(*sorted(zip(versions, paths)))
            versions, paths = list(versions), list(paths)

        for i in range(1, len(versions)):
            if versions[i] == versions[i - 1]:
                msg = f'{paths[i]} and {paths[i - 1]} are defined as migration steps for the same target version'
                raise ValueError(msg)

        indices = {v: i for i, v in enumerate(versions)}

        self.__version_indices = indices
        self.__versions = versions
        self.__steps_paths = paths


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
