# SPDX-License-Identifier: MPL-2.0
"""
ASB implementation for MongoDB, which is provided by the class `MongoASB`.
"""
from __future__ import annotations

import datetime
import pathlib
import shlex
import subprocess
import typing as T

import semantic_version as semver
import pymongo.database
import pymongo.collection

from .. import (
    migration,
    appstate,
)


class MongoASBConf:
    """
    Configuration object for `MongoASB`.
    """

    def __init__(self,
        versioning_collection: str = 'svip_versioning',
        backups_dir: pathlib.Path = pathlib.Path('migration-backups'),
        cli_connection_options: list[str] = None,
        cli_authentication_options: list[str] = [],
        cli_dump_prefix: list[str] = ['mongodump'],
        cli_restore_prefix: list[str] = ['mongorestore'],
        cli_dump_extra_options: list[str] = [],
        cli_restore_extra_options: list[str] = [],
    ):
        """
        Initialize the configuration object. All parameter arguments are
        assigned to attributes of the same name.

        The parameters with name prefixed by "cli_" are parameters used when
        performing backup and restore of the database.

        :param versioning_collection: name of the collection to store data
          related to versioning.

        :param backups_dir: path to the directory that is supposed to contain
          backup files.

        :param cli_connection_options: list of CLI options related to
          connecting to the mongo instance (i.e. '--host' and '--port'). This
          list is used for composing the command for both ``mongodump`` and
          ``mongorestore``. If this parameter is omitted, then the host and
          port values from the mongo connection object passed to `MongoASB`'s
          constructor is used.  You can pass an empty list for this parameter
          if you do not want the default behavior.

        :param cli_authentication_options: list of CLI options related to
          authentication. This list is used for composing the command for both
          ``mongodump`` and ``mongorestore``.

        :param cli_dump_prefix: a list to serve as the command that will call
          ``mongodump``. By default, this is ``['mongodump']``, but you can
          override it if ``mongodump`` must be called differently (e.g. when it
          must be called via a docker command).

        :param cli_restore_prefix: a list to serve as the command that will
          call ``mongorestore``. By default, this is ``['mongorestore']``, but
          you can override it if ``mongodump`` must be called differently (e.g.
          when it must be called via a docker command).

        :param cli_dump_extra_options: a list of extra options for
          ``mongodump``.

        :param cli_restore_extra_options: a list of extra options for
          ``mongorestore``.
        """
        self.versioning_collection = versioning_collection
        self.backups_dir = pathlib.Path(backups_dir)
        self.cli_connection_options = cli_connection_options
        self.cli_authentication_options = cli_authentication_options
        self.cli_dump_prefix = cli_dump_prefix
        self.cli_restore_prefix = cli_restore_prefix
        self.cli_dump_extra_options = cli_dump_extra_options
        self.cli_restore_extra_options = cli_restore_extra_options


class MongoASBBackup(appstate.AppStateBackup):
    def __init__(self,
            db: pymongo.database.Database,
            path: pathlib.Path,
            conf: MongoASBConf,
            is_in_migration: bool,
        ):
        path = pathlib.Path(path)
        if path.exists():
            raise RuntimeError(f'refusing to do backup: path {path} exists')

        db_name = db.name
        host, port = db.client.address

        if conf.cli_connection_options is None:
            cli_connection_options = ( # pragma: no cover
                '--host', host,
                '--port', port,
            )
        else:
            cli_connection_options = tuple()

        cmd = (
            *conf.cli_dump_prefix,
            *cli_connection_options,
            *conf.cli_authentication_options,
            *conf.cli_dump_extra_options,
            '--db', db_name,
            '--gzip',
            '--archive',
        )
        cmd = tuple(str(v) for v in cmd)

        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'wb') as f:
            subprocess.run(
                cmd,
                check=True,
                stdout=f,
            )

        self.__path = path
        self.__host = host
        self.__port = port
        self.__db_name = db_name
        self.__conf = conf
        self.__is_in_migration = is_in_migration

    def restore(self):
        cmd = self.__get_restore_cmd(mask_auth_options=False)
        with open(self.__path, 'rb') as f:
            subprocess.run(
                cmd,
                check=True,
                stdin=f,
            )

    def info(self):
        lines = [f'backup is at: {self.__path}']
        if not self.__is_in_migration:
            lines.append('you can pass it as the standard input to the following command to restore the backup:')
            cmd = self.__get_restore_cmd(mask_auth_options=True)
            cmd = ' '.join(shlex.quote(part) for part in cmd)
            lines.append(f'    {cmd}')
        return '\n'.join(lines)

    def __get_restore_cmd(self, mask_auth_options: bool):
        if self.__conf.cli_connection_options is None:
            cli_connection_options = ( # pragma: no cover
                '--host', self.__host,
                '--port', self.__port,
            )
        else:
            cli_connection_options = tuple()

        cli_authentication_options = self.__conf.cli_authentication_options
        if mask_auth_options and cli_authentication_options:
            cli_authentication_options = ('MASKED_AUTH_OPTIONS',)

        cmd = (
            *self.__conf.cli_restore_prefix,
            *cli_connection_options,
            *cli_authentication_options,
            *self.__conf.cli_restore_extra_options,
            '--drop',
            '--gzip',
            '--archive',
        )
        cmd = tuple(str(v) for v in cmd)
        return cmd


class MongoASBTestInterface(appstate.AppStateTestInterface):
    def __init__(self, coll: pymongo.collection.Collection):
        self.__coll = coll

    def set_version_no_restrictions(self,
        current: semver.Version,
        target: semver.Version,
    ):
        new_current = str(current)
        new_target = str(target) if target else None

        r = self.__coll.update_one(
            filter={'_id': 'svip_versioning'},
            update={
                '$set': {
                    'current_version': new_current,
                    'target_version': new_target,
                },
            },
        )

        if not r.acknowledged:
            raise RuntimeError('update not aknowledged') # pragma: no cover

        if not r.matched_count:
            raise RuntimeError('no document matched for the update') # pragma: no cover

    def set_string(self, s: str):
        r = self.__coll.update_one(
            filter={'_id': 'svip_versioning'},
            update={
                '$set': {'test_interface_set_string_data': s},
            },
        )

        if not r.acknowledged:
            raise RuntimeError('update not aknowledged') # pragma: no cover

        if not r.matched_count:
            raise RuntimeError('no document matched for the update') # pragma: no cover

    def get_string(self):
        data = self.__coll.find_one(
            'svip_versioning',
            {'test_interface_set_string_data': 1},
        )
        return data['test_interface_set_string_data']


class MongoASB(appstate.AppStateBackend):
    """
    The ASB implementation for MongoDB.
    """

    def __init__(self, conf: MongoASBConf, db: pymongo.database.Database):
        """
        Initialize the ASB object.

        :param conf: the configuration for this ASB.

        :param conf: the pymongo object representing the database used by the
          application.
        """
        self.__db = db
        self.__conf = conf
        self.__coll = self.__db.get_collection(self.__conf.versioning_collection)

        # Try inserting initial versioning data. If that was already done
        # before, just ignore the DuplicateKeyError.
        try:
            r = self.__coll.insert_one({
                '_id': 'svip_versioning',
                'current_version': '0.0.0',
                'target_version': None,
                'set_version_info': None,
                'inconsistency': None,
                'history': [],
            })
        except pymongo.errors.DuplicateKeyError:
            pass
        else:
            if not r.acknowledged:
                msg = 'failed to initialize versioning information: insert not aknowledged' # pragma: no cover
                raise RuntimeError(msg) # pragma: no cover

    def set_version(self,
        current: semver.Version,
        target: semver.Version,
    ) -> T.Tuple[bool, semver.Version, semver.Version]:
        new_current = str(current)
        new_target = str(target) if target else None

        condition = {'$and': [
            # Condition (1) of set_version(): either ``target_before is None``
            # or ``target is None`` (exclusive "or"):
            {'$or': [
                {'$and': [
                    {'$eq': ['$target_version', None]},
                    {'$ne': [new_target, None]},
                ]},
                {'$and': [
                    {'$ne': ['$target_version', None]},
                    {'$eq': [new_target, None]},
                ]},
            ]},
            # Condition (2) of set_version(): ``current_before != current`` if,
            # and only if, ``current = target_before`` and ``target is None``:
            {'$eq': [
                {'$ne': ['$current_version', new_current]},
                {'$and': [
                    {'$eq': [new_current, '$target_version']},
                    {'$eq': [new_target, None]},
                ]}
            ]},
        ]}

        update = [{
            '$set': {
                'target_version': {
                    '$cond': {
                        'if': condition,
                        'then': new_target,
                        'else': '$target_version',
                    },
                },
                'current_version': {
                    '$cond': {
                        'if': condition,
                        'then': new_current,
                        'else': '$current_version',
                    },
                },
                'set_version_info': {
                    'condition': condition,
                    'prev_current_version': '$current_version',
                    'prev_target_version': '$target_version',
                },
                'history': {
                    '$cond': {
                        'if': {'$and': [
                            condition,
                            {'$eq': [new_current, '$target_version']},
                        ]},
                        'then': {'$concatArrays': [
                            '$history',
                            [[new_current, datetime.datetime.utcnow()]],
                        ]},
                        'else': '$history',
                    },
                },
            },
        }]
        r = self.__coll.find_one_and_update(
            filter={'_id': 'svip_versioning'},
            update=update,
            projection={
                'current_version': 1,
                'target_version': 1,
                'set_version_info': 1,
            },
            return_document=pymongo.ReturnDocument.AFTER,
        )

        info = r['set_version_info']
        updated = info['condition']

        prev_current = semver.Version(info['prev_current_version'])

        prev_target = None
        if info['prev_target_version']:
            prev_target = semver.Version(info['prev_target_version'])

        return updated, prev_current, prev_target

    def get_version(self) -> T.Tuple[semver.Version, semver.Version]:
        data = self.__coll.find_one(
            'svip_versioning',
            {'current_version': 1, 'target_version': 1},
        )
        current = semver.Version(data['current_version'])
        target = None
        if data['target_version']:
            target = semver.Version(data['target_version'])
        return current, target

    def register_inconsistency(self, info: str, backup_info: str = None):
        r = self.__coll.update_one(
            {'_id': 'svip_versioning'},
            {'$set': {'inconsistency': [info, backup_info]}},
        )

        if not r.acknowledged:
            raise RuntimeError('update not aknowledged') # pragma: no cover

        if not r.matched_count:
            raise RuntimeError('no document matched for the update') # pragma: no cover

    def get_inconsistency(self) -> T.Union[None, T.Tuple[str, str]]:
        data = self.__coll.find_one(
            'svip_versioning',
            {'inconsistency': 1},
        )
        return tuple(data['inconsistency']) if data['inconsistency'] else None

    def clear_inconsistency(self):
        r = self.__coll.update_one(
            {'_id': 'svip_versioning'},
            {'$set': {'inconsistency': None}},
        )

        if not r.acknowledged:
            raise RuntimeError('update not aknowledged') # pragma: no cover

        if not r.matched_count:
            raise RuntimeError('no document matched for the update') # pragma: no cover

    def get_version_history(self) -> T.List[T.Tuple[semver.Version, datetime.datetime]]:
        data = self.__coll.find_one(
            'svip_versioning',
            {'history': 1},
        )
        return [
            (semver.Version(version), timestamp)
            for version, timestamp in data['history']
        ]

    def backup(self, info: T.Union[None, migration.MigrationInfo]) -> MongoASBBackup:
        t = datetime.datetime.utcnow()
        dir_name = t.strftime('%Y-%m-%d_%H:%M:%S-svip-mongo-asb-backup.gz')
        backup_dir = self.__conf.backups_dir / dir_name
        return MongoASBBackup(
            db=self.__db,
            path=backup_dir,
            conf=self.__conf,
            is_in_migration=info is not None,
        )

    def backup_supports_restore(self) -> bool:
        return True

    def get_test_interface(self) -> MongoASBTestInterface:
        return MongoASBTestInterface(self.__coll)
