"""
This module provides the `AppStateMock` class, which simulates the
functionality required for application state back ends.
"""
from __future__ import annotations

import semantic_version as semver

import copy
import datetime
import itertools
import typing as T

import svip


class AppStateMock:
    """
    An `AppStateMock` object provides the attribute `asb` as an application
    state back end that can be used in tests.

    The provided ASB implements a very simplistic state management
    functionality by keeping an state object and providing the functionality
    required for subclasses of `svip.AppStateBackend`.

    Along with the `asb` property, an instance of this class also provides:

    - ways to control the behavior of the back end via constructor parameters;

    - and methods to read and update data: `get_data()`, `set_data()` and
      `get_snapshot()`.
    """

    mock_class_counter = itertools.count()
    """
    Counter to ensure unique class names are generated when creating subclasses
    of `AppStateBackend`.
    """

    def __init__(self,
        current_version: semver.Version = semver.Version('0.0.0'),
        target_version: semver.Version = None,
        version_history:  T.List[T.Tuple[semver.Version, datetime.datetime]] = None,
        inconsistency: T.Union[None, T.Tuple[str, str]] = None,
        with_backup: bool = True,
        with_backup_restore: T.Union[None, bool] = True,
        fail_restore_backup: bool = False,
        with_transaction: bool = True,
        fail_rollback: bool = False,
        with_version_history: bool = True,
        asb_overrides: T.Dict[str, T.Any] = None,
    ):
        """
        Initializes the mock object.

        A subclass of `AppStateBackend` is created and used to instantiate an
        object that is assigned to the ``asb`` property. The behavior of the
        provided ASB can be controlled with the parameters passed to the
        contructor:

        :param current_version: the initial value for the current schema
          version.

        :param target_version: the initial value for the target schema version.

        :param inconsistency: if not None, initialize the internal state as
          inconsistent. In that case, the value must be a tuple that would be
          retured by the method `AppStateBackend.get_inconsistency()`.

        :param with_backup: controls whether the ASB must support backups.

        :param with_backup_restore: controls whether the ASB must support
          restoring backups. If it is a boolean, then it will be the value
          returned by `AppStateBackend.backup_supports_restore()`. If the value
          is None, then the default implementation of
          `AppStateBackend.backup_supports_restore()` will be used.

        :param with_transaction: controls whether the ASB must support
          transactions. The created transaction object is not a real
          transaction: it only supports restoring the state if an error occurs.

        :param fail_rollback: controls whether a transaction must fail to
          rollback.

        :param with_version_history: controls whether
          `AppStateBackend.get_version_history()` must be implemented.

        :param asb_overrides: If provided, the created `AppStateBackend`
          subclass is also subclassed using `asb_overrides` as its dict. In
          that case, this new class is used for instantiating the ASB object.
        """
        self.__state = {
            'current_version': current_version,
            'target_version': target_version,
            'version_history': list(version_history) if version_history else [],
            'inconsistency': inconsistency,
            'data': None,
        }
        self.__create_asb(
            with_backup=with_backup,
            fail_restore_backup=fail_restore_backup,
            with_transaction=with_transaction,
            with_backup_restore=with_backup_restore,
            fail_rollback=fail_rollback,
            with_version_history=with_version_history,
            overrides=asb_overrides,
        )

    def __create_asb(self,
        with_backup: bool = True,
        with_backup_restore: T.Union[None, bool] = True,
        fail_restore_backup: bool = True,
        with_transaction: bool = True,
        fail_rollback: bool = False,
        with_version_history: bool = True,
        overrides: dict = True,
    ):
        """
        Dynamically create a subclass of ``AppStateBackend``, instantiate
        the object and assign it to ``self.asb``.
        """
        cls_name = f'AppStateMock{next(self.mock_class_counter)}'
        cls_bases = (svip.AppStateBackend,)
        cls_dict = {}

        # A decorator to make things simpler
        def method(fn=None, cond=True):
            def decorator(f):
                if cond:
                    cls_dict[f.__name__] = f
                return f
            if fn:
                return decorator(fn)
            else:
                return decorator

        # Create methods!
        @method
        def set_version(asb, current, target):
            current_before, target_before = asb.get_version()

            is_update_valid = (
                (
                    # First condition documented in AppStateBackup.set_version
                    (target_before is None and target is not None) or
                    (target_before is not None and target is None)
                ) and (
                    # Second condition documented in AppStateBackup.set_version
                    (current_before != current) ==
                    (current == target_before and target is None)
                )
            )
            if is_update_valid:
                self.__state['current_version'] = current
                self.__state['target_version'] = target
            return is_update_valid, current_before, target_before

        @method
        def register_inconsistency(asb, info, backup_info):
            self.__state['inconsistency'] = info, backup_info

        @method
        def get_inconsistency(asb):
            return self.__state['inconsistency']

        @method
        def clear_inconsistency(asb):
            self.__state['inconsistency'] = None

        @method
        def get_version(asb):
            return self.__state['current_version'], self.__state['target_version']

        @method(cond=with_version_history)
        def get_version_history(self):
            return copy.deepcopy(self.__state['version_history'])

        def restore_state(saved_state):
            self.__state = saved_state

        def copy_state():
            return copy.deepcopy(self.__state)

        @method(cond=with_backup)
        def backup(asb, info):

            class Backup(svip.AppStateBackup):
                def __init__(bkp, info):
                    bkp.__saved_state = copy_state()

                if with_backup_restore:
                    def restore(bkp):
                        if fail_restore_backup:
                            raise Exception('backup restore failed on purpose')
                        restore_state(self.__saved_state)

            return Backup(copy_state())

        @method(cond=with_backup and with_backup_restore is not None)
        def backup_supports_restore(asb):
            return with_backup_restore

        @method(cond=with_transaction)
        def transaction(self):
            class PseudoTransaction(svip.AppStateTransaction):
                def __init__(trs):
                    trs.__entered = False
                    trs.__rollback_successful = False

                def __enter__(trs):
                    if trs.__entered:
                        raise RuntimeError('cannot enter transaction more than once')
                    trs.__entered = True
                    trs.__saved_state = copy_state()

                def __exit__(trs, exc_type, exc_val, exc_tb):
                    if exc_type is None:
                        return False
                    if not fail_rollback:
                        restore_state(trs.__saved_state)
                        trs.__rollback_successful = True
                    return False

                def rollback_successful(trs):
                    return trs.__rollback_successful

            return PseudoTransaction()

        @method
        def get_test_interface(asb):
            state_ref = self.__state
            class TestInterface(svip.AppStateTestInterface):
                def set_version_no_restrictions(ti, current, target):
                    state_ref['current_version'] = current
                    state_ref['target_version'] = target
            return TestInterface()

        cls = type(cls_name, cls_bases, cls_dict)

        if overrides:
            cls = type(f'{cls_name}_Overriden', (cls,), overrides)

        self.asb = cls()

    def get_data(self) -> T.Any:
        """
        Return a deep copy of the internal data (excluding state related to
        versioning).

        This method can be used by migration steps as well as test code.
        """
        return copy.deepcopy(self.__state['data'])

    def set_data(self, data: T.Any):
        """
        Make a deep copy of `data` and replace the internal data with it.

        This only replaces data not related to versioning. This method can be
        used by migration steps as well as test code.
        """
        self.__state['data'] = copy.deepcopy(data)

    def get_snapshot(self) -> T.Any:
        """
        Return a snapshot of the entire internal state.

        This method can be used by test code.
        """
        return copy.deepcopy(self.__state)
