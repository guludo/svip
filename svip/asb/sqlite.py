# SPDX-License-Identifier: MPL-2.0
"""
ASB implementation for SQLite, which is provided by the class `SqliteASB`.
"""
from __future__ import annotations

import contextlib
import datetime
import json
import pathlib
import sqlite3
import typing as T

import semantic_version as semver

from .. import (
    appstate,
)


class SqliteASB(appstate.AppStateBackend):
    """
    The ASB implementation for Sqlite.
    """

    def __init__(self, conn: sqlite3.Connection, conf: SqliteASBConf):
        self.__conn = conn
        self.__conf = conf

    def set_version(self,
        current: semver.Version,
        target: semver.Version,
    ) -> T.Tuple[bool, semver.Version, semver.Version]:
        return self.__set_version(current, target, False)

    def __set_version_no_restrictions(self,
        current: semver.Version,
        target: semver.Version,
    ):
        updated, *_ = self.__set_version(current, target, True)
        if not updated:
            raise RuntimeError("unrestricted set_version operation did not match any row")  # pragma: no cover

    def __set_version(self,
        current: semver.Version,
        target: semver.Version,
        no_restrictions: bool,
    ) -> T.Tuple[bool, semver.Version, semver.Version]:
        updated = False

        with self.__transaction() as cur:
            self.__ensure_versioning_table(cur)

            cur.execute(
                f"""
                SELECT current_version, target_version, version_history_json
                FROM `{self.__conf.versioning_table}`
                """
            )
            t = cur.fetchone()
            prev_current = semver.Version(t[0])
            prev_target = semver.Version(t[1]) if t[1] else None
            prev_history_json = t[2]
            if current == prev_target:
                history = json.loads(prev_history_json)
                history.append((str(current), int(datetime.datetime.utcnow().timestamp())))
                history_json = json.dumps(history)
            else:
                history_json = prev_history_json

            update_stmt = f"""
            UPDATE `{self.__conf.versioning_table}`
            SET
                current_version = :new_current,
                target_version = :new_target,
                version_history_json = :new_history_json
            """

            if not no_restrictions:
                update_stmt += """
                WHERE
                    (
                      (target_version ISNULL AND :new_target NOTNULL)
                      OR
                      (target_version NOTNULL AND :new_target ISNULL)
                    )
                    AND
                    (current_version != :new_current)
                        == (target_version == :new_current AND :new_target ISNULL)
                """

            cur.execute(
                update_stmt,
                {
                    "new_current": str(current),
                    "new_target": str(target) if target else None,
                    "new_history_json": history_json if not no_restrictions else prev_history_json,
                },
            )
            updated = cur.rowcount > 0

        return updated, prev_current, prev_target

    def get_version(self) -> T.Tuple[semver.Version, semver.Version]:
        with self.__transaction() as cur:
            if not self.__versioning_table_exists(cur):
                return semver.Version("0.0.0"), None

            res = cur.execute(
                f"SELECT current_version, target_version FROM `{self.__conf.versioning_table}`"
            )
            t = res.fetchone()
            current = semver.Version(t[0])
            target = semver.Version(t[1]) if t[1] else None
            return current, target

    def register_inconsistency(self, info: str, backup_info: str = None):
        with self.__transaction() as cur:
            self.__ensure_versioning_table(cur)
            cur.execute(
                f"""
                UPDATE `{self.__conf.versioning_table}`
                SET
                    inconsistency_info = ?,
                    inconsistency_backup_info = ?
                """,
                (info, backup_info),
            )

            if cur.rowcount <= 0:
                raise RuntimeError("no row matched for the updated")  # pragma: no cover

    def get_inconsistency(self) -> T.Union[None, T.Tuple[str, str]]:
        with self.__transaction() as cur:
            if not self.__versioning_table_exists(cur):
                return None

            res = cur.execute(
                f"""
                SELECT inconsistency_info, inconsistency_backup_info
                FROM `{self.__conf.versioning_table}`
                """
            )
            t = res.fetchone()
            return t if t[0] else None

    def clear_inconsistency(self):
        with self.__transaction() as cur:
            cur.execute(
                f"""
                UPDATE `{self.__conf.versioning_table}`
                SET
                    inconsistency_info = NULL,
                    inconsistency_backup_info = NULL
                """,
            )

            if cur.rowcount <= 0:
                raise RuntimeError("no row matched for the updated")  # pragma: no cover

    def get_version_history(self) -> T.List[T.Tuple[semver.Version, datetime.datetime]]:
        with self.__transaction() as cur:
            cur.execute(
                f"""
                SELECT version_history_json FROM `{self.__conf.versioning_table}`
                """,
            )
            ret = [
                (semver.Version(version), datetime.datetime.utcfromtimestamp(timestamp))
                for version, timestamp in json.loads(cur.fetchone()[0])
            ]
            return ret

    def backup(self, info: T.Union[None, migration.MigrationInfo]) -> MongoASBBackup:
        t = datetime.datetime.utcnow()
        filename = t.strftime('%Y-%m-%d_%H:%M:%S-svip-sqlite-asb-backup.db')
        return SqliteASBBackup(
            src_conf=self.__conf,
            src_conn=self.__conn,
            path=self.__conf.backups_dir / filename,
        )

    def backup_supports_restore(self) -> bool:
        # Simply replacing the original database with the backup might be
        # problematic[1]. Thus, we do not support backup restoration at the
        # moment; the user must ensure that she can safely replace the original
        # file with the backup and do it herself.
        #
        # [1] https://sqlite.org/howtocorrupt.html#_unlinking_or_renaming_a_database_file_while_in_use
        return False

    def get_test_interface(self) -> MongoASBTestInterface:
        return _SqliteASBTestInterface(
            self.__conn,
            set_version_no_restrictions=self.__set_version_no_restrictions,
        )

    @contextlib.contextmanager
    def transaction(self):
        with self.__transaction():
            yield

    @contextlib.contextmanager
    def __transaction(self):
        cur = self.__conn.cursor()
        cur.row_factory = None
        cur.execute(f"BEGIN EXCLUSIVE")
        try:
            yield cur
        except:
            self.__conn.rollback()
            raise
        else:
            self.__conn.commit()
        finally:
            cur.close()

    def __ensure_versioning_table(self, cur):
        if self.__versioning_table_exists(cur):
            return

        cur.execute(f"""
        CREATE TABLE `{self.__conf.versioning_table}` (
            /* We need to bump sqlite_asb_version is if we ever need to change
             * the structure of this table. */
            sqlite_asb_version,
            current_version,
            target_version,
            inconsistency_info,
            inconsistency_backup_info,
            version_history_json
        )
        """)

        cur.execute(f"""
            INSERT INTO `{self.__conf.versioning_table}` (
                sqlite_asb_version,
                current_version,
                target_version,
                inconsistency_info,
                inconsistency_backup_info,
                version_history_json
            )
            VALUES (
                1,
                '0.0.0',
                NULL,
                NULL,
                NULL,
                '[]'
            )
        """)

    def __versioning_table_exists(self, cur):
        cur.execute(
            "SELECT count(*) FROM sqlite_schema WHERE type = 'table' AND name == ?",
            (self.__conf.versioning_table,),
        )
        return cur.fetchone()[0] > 0


class _SqliteASBTestInterface(appstate.AppStateTestInterface):
    def __init__(self, conn, set_version_no_restrictions):
        self.__conn = conn
        self.__set_version_no_restrictions = set_version_no_restrictions

    def set_version_no_restrictions(self,
        current: semver.Version,
        target: semver.Version,
    ):
        self.__set_version_no_restrictions(current, target)

    def set_string(self, s):
        cur = self.__conn.cursor()
        cur.row_factory = None
        cur.execute(
            """
            SELECT count(*) FROM sqlite_schema
            WHERE type = 'table' AND name == 'testing_interface_data'
            """,
        )
        if cur.fetchone()[0] == 0:
            cur.execute(
                """
                CREATE TABLE testing_interface_data (
                    set_string_data
                )
                """,
            )
            cur.execute(
                """
                INSERT INTO testing_interface_data VALUES (
                    ?
                )
                """,
                (s,)
            )
        else:
            cur.execute(
                """
                UPDATE testing_interface_data
                SET set_string_data = ?
                """,
                (s,)
            )

    def get_string(self):
        cur = self.__conn.cursor()
        cur.row_factory = None
        return cur.execute(
            """
            SELECT set_string_data FROM testing_interface_data
            """,
        ).fetchone()[0]


class SqliteASBConf:
    def __init__(self,
        versioning_table: str = "svip_versioning",
        backups_dir: pathlib.Path = pathlib.Path('migration-backups'),
    ):
        self.versioning_table = versioning_table
        self.backups_dir = pathlib.Path(backups_dir)


class SqliteASBBackup(appstate.AppStateBackup):
    def __init__(self, src_conf, src_conn, path):
        self.__src_conf = src_conf
        self.path = path
        self.path.parent.mkdir(exist_ok=True, parents=True)
        bkp_conn = sqlite3.connect(self.path)
        with bkp_conn:
            src_conn.backup(bkp_conn)
        bkp_conn.close()

    def info(self):
        return f"a backup of the database file is available at: {self.path}"
