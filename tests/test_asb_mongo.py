import datetime
import itertools
import pathlib
import subprocess

import pytest
import semantic_version as semver

import asb_testing
import svip.migration


# The ASB for mongo depends on pymongo to be available.
pytest.importorskip('pymongo')

# Skip if docker is not available
try:
    subprocess.run(['docker', '--version'], stdout=None, check=True)
except FileNotFoundError:
    pytest.skip('docker command is not available', allow_module_level=True)


# If we got here, we know that we can import pytest_mongo
import pytest_mongo.executor_noop
import pytest_mongo.factories


@pytest.fixture(scope='session')
def mongo_service():
    """
    Fixture that starts a mongo service and yields useful information in a
    dictionary.
    """
    container_id = subprocess.run(
        ['docker', 'run', '--rm', '-d', '-p', '27017', 'mongo:4'],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()

    try:
        # Get published port
        port_lines = subprocess.run(
            ['docker', 'container', 'port', container_id, '27017/tcp'],
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.splitlines()

        ip, port = port_lines[0].rsplit(':')

        info = {
            'exec_prefix': ['docker', 'exec', '-i', container_id],
            'host': ip,
            'port': int(port),
        }

        yield info
    finally:
        subprocess.run(
            ['docker', 'kill', container_id],
            check=True,
            stdout=subprocess.DEVNULL,
        )


# NOTE:
#  Overriding mongo_noproc and using duck-typing here in order to provide the
#  TCP port exported by docker to pytest-mongo at runtime. Let's keep an eye on
#  https://github.com/ClearcodeHQ/pytest-mongo/issues/308 . If the feature
#  proposed there is implemented, then we can provide the configuration in a
#  proper way.
@pytest.fixture(scope='session')
def mongo_noproc(mongo_service):
    yield pytest_mongo.executor_noop.NoopExecutor(
        host=mongo_service['host'],
        port=mongo_service['port'],
    )


mongo_connection = pytest_mongo.factories.mongodb('mongo_noproc')


@pytest.fixture
def asb_factory(tmp_path, mongo_connection, mongo_service):
    import svip.asb.mongo

    counter = itertools.count()

    def asb():
        return svip.asb.mongo.MongoASB(
            conf=svip.asb.mongo.MongoASBConf(
                backups_dir=tmp_path / str(next(counter)) / 'backups',
                cli_dump_prefix=mongo_service['exec_prefix'] + ['mongodump'],
                cli_restore_prefix=mongo_service['exec_prefix'] + ['mongorestore'],
                cli_connection_options=[],
            ),
            db=mongo_connection.get_database('foo'),
        )

    yield asb


@pytest.fixture
def asb(asb_factory):
    yield asb_factory()


def test_data_already_initialized(asb_factory):
    asb1 = asb_factory()
    asb2 = asb_factory()


def test_backup_info(asb):
    migration_info = svip.migration.MigrationInfo(
        current=semver.Version('0.0.0'),
        target=semver.Version('0.0.1'),
    )
    bkp = asb.backup(migration_info)
    bkp_info = bkp.info()
    assert bkp_info.startswith('backup is at: ')
    assert bkp_info.endswith('-svip-mongo-asb-backup.gz')


def test_duplicate_backup_output(asb, monkeypatch):
    migration_info = svip.migration.MigrationInfo(
        current=semver.Version('0.0.0'),
        target=semver.Version('0.0.1'),
    )

    # Let's mock datetime.datetime to return always the same value for utcnow()
    # since the backup filename is generated using that function.
    class MockedDatetime:
        fixed_now = datetime.datetime.utcnow()

        @staticmethod
        def utcnow():
            return MockedDatetime.fixed_now

    monkeypatch.setattr(datetime, 'datetime', MockedDatetime)

    first_bkp = asb.backup(migration_info)
    with pytest.raises(
        RuntimeError,
        match=r'^refusing to do backup: path .*-svip-mongo-asb-backup\.gz exists$',
    ):
        second_bkp = asb.backup(migration_info)


globals().update(asb_testing.generate_tests('mongo', supports_transaction=False))
