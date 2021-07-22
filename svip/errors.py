"""
This module provides `Exception` subclasses used by SVIP for errors.
"""

class ErrorBase(Exception):
    """
    Base class for errors in SVIP.
    """
    pass


class BackupNotImplementedError(ErrorBase):
    pass


class BackupFailedError(ErrorBase):
    pass


class IncompatibleVersionError(ErrorBase):
    pass


class InconsistentStateError(ErrorBase):
    pass


class InvalidStepSource(ErrorBase):
    pass


class IrreversibleStepError(ErrorBase):
    pass


class MigrationError(ErrorBase):
    pass


class MigrationInProgressError(ErrorBase):
    pass


class NoGuardrailsError(ErrorBase):
    pass


class RestoreFailedError(ErrorBase):
    def __init__(self, msg, original_error: Exception):
        super().__init__(msg)
        self.original_error = original_error


class RestoreNotImplementedError(ErrorBase):
    pass


class TransactionFailedError(ErrorBase):
    pass


class UnrecognizedScriptFound(ErrorBase):
    pass


class VersionNotFoundError(ErrorBase):
    pass
