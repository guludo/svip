import contextlib
import io

import pytest

import svip


@pytest.mark.parametrize('verbose', ['verbose', 'non-verbose'])
def test_backup(svip_factory, verbose):
    sv, _ = svip_factory()
    with contextlib.redirect_stdout(io.StringIO()) as f:
        bkp = sv.backup(verbose=verbose == 'verbose')
    assert isinstance(bkp, svip.AppStateBackup)

    output = f.getvalue()
    if verbose == 'verbose':
        expected_prefix = (
            'Saving backup...\n'
            'Backup information:\n'
        )
    else:
        expected_prefix = ''
    assert output.startswith(expected_prefix)

def test_backup_not_implemented(svip_factory):
    sv, _ = svip_factory(with_backup=False)
    with pytest.raises(svip.errors.BackupNotImplementedError):
        sv.backup()
