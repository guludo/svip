import svip


# A dummy subclass with an empty implementation of each abstract method
AppStateDummy = type(
    'AppStateDummy',
    (svip.AppStateBackend,),
    {
        name: lambda self, *k, **kw: None
        for name in (
            k for k, v in vars(svip.appstate.AppStateBackend).items()
            if k[0].isalpha() and getattr(v, '__isabstractmethod__', False)
        )
    },
)


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
