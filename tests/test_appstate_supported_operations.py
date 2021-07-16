import svip.appstate


def test_supports_backup():
    class AppStateWithoutBackup(svip.appstate.AppStateBackend):
        pass

    assert AppStateWithoutBackup().supports_backup() == False

    class AppStateWithBackup(svip.appstate.AppStateBackend):
        def backup():
            pass

    assert AppStateWithBackup().supports_backup() == True


def test_supports_transaction():
    class AppStateWithoutTransaction(svip.appstate.AppStateBackend):
        pass

    assert AppStateWithoutTransaction().supports_transaction() == False

    class AppStateWithTransaction(svip.appstate.AppStateBackend):
        def transaction():
            pass

    assert AppStateWithTransaction().supports_transaction() == True
