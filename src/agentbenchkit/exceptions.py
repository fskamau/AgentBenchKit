"""User-facing errors with stable diagnostic codes."""


class BenchKitError(Exception):
    """Expected validation or execution problem."""

    def __init__(self, message: str, code: str = "agentbenchkit_error") -> None:
        super().__init__(message)
        self.code = code


class ExecutionDenied(BenchKitError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "execution_denied")


class InvalidPatch(BenchKitError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "invalid_patch")
