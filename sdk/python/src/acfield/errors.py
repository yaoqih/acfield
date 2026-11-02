"""Errors shared by the HTTP client and managed control sessions."""


class ACFieldError(Exception):
    """Base error raised by the SDK (invalid local arguments use ValueError)."""


class TransportError(ACFieldError):
    """Connection, network or timeout failure; request outcome may be unknown."""


class APIError(ACFieldError):
    """The server rejected a request. ``detail`` preserves its JSON explanation."""

    def __init__(self, status_code: int, detail: object, method: str, path: str):
        self.status_code = status_code
        self.detail = detail
        self.method = method
        self.path = path
        super().__init__(f"{method} {path}: HTTP {status_code}: {detail}")


class ProtocolError(ACFieldError):
    """A successful response did not match the expected wire format."""


class ControlError(ACFieldError):
    """A session cannot acquire or retain the requested control conditions."""


class CleanupError(ACFieldError):
    """One or more owned-control release requests could not be confirmed."""

    def __init__(self, failures: dict[str, ACFieldError]):
        self.failures = failures
        super().__init__("Control release failed: " + "; ".join(
            f"{ident}: {error}" for ident, error in failures.items()))
