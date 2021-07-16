import svip.appstate

class AppStateDummy(svip.appstate.AppStateBackend):
    def set_version(self, *k, **kw):
        pass

    def get_version(self, *k, **kw):
        pass


def test_supports_backup():
    class AppStateWithoutBackup(AppStateDummy):
        pass

    assert AppStateWithoutBackup().supports_backup() == False

    class AppStateWithBackup(AppStateDummy):
        def backup():
            pass

    assert AppStateWithBackup().supports_backup() == True


def test_supports_transaction():
    class AppStateWithoutTransaction(AppStateDummy):
        pass

    assert AppStateWithoutTransaction().supports_transaction() == False

    class AppStateWithTransaction(AppStateDummy):
        def transaction():
            pass

    assert AppStateWithTransaction().supports_transaction() == True
