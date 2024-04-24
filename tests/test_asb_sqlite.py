# SPDX-License-Identifier: MPL-2.0
import sqlite3

import pytest
import semantic_version as semver

import asb_testing
import svip.migration


@pytest.fixture
def asb(tmp_path):
    import svip.asb.sqlite

    conf = svip.asb.sqlite.SqliteASBConf(backups_dir=tmp_path / "backups")
    conn = sqlite3.connect(":memory:")
    try:
        yield svip.asb.sqlite.SqliteASB(conn, conf)
    finally:
        conn.close()


@pytest.mark.parametrize(
    'with_migration',
    ['with_migration', 'without_migration'],
)
def test_backup(asb, with_migration):
    if with_migration == 'with_migration':
        migration_info = svip.migration.MigrationInfo(
            current=semver.Version('0.0.0'),
            target=semver.Version('0.0.1'),
        )
    else:
        migration_info = None

    with asb._SqliteASB__transaction() as cur:
        cur.execute("CREATE TABLE foo(a, b)")
        cur.execute("INSERT INTO foo(a, b) VALUES (1, 2), (3, 4)")

    bkp = asb.backup(migration_info)
    assert str(bkp.path) in bkp.info()

    conn = sqlite3.connect(bkp.path)
    rows = conn.execute("SELECT * from foo").fetchall()
    assert rows == [(1, 2), (3, 4)]

globals().update(asb_testing.generate_tests('sqlite', backup_supports_restore=False))
