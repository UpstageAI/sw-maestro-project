class RefreshCancelled(Exception):
    """Raised when a refresh run is cancelled by the client."""


class RefreshCancellationRegistry:
    def __init__(self):
        self._active: set[str] = set()
        self._cancelled: set[str] = set()

    def register(self, run_id: str | None) -> None:
        if not run_id:
            return
        self._active.add(run_id)
        self._cancelled.discard(run_id)

    def cancel(self, run_id: str | None) -> None:
        if not run_id:
            return
        self._cancelled.add(run_id)

    def complete(self, run_id: str | None) -> None:
        if not run_id:
            return
        self._active.discard(run_id)
        self._cancelled.discard(run_id)

    def check(self, run_id: str | None) -> None:
        if run_id and run_id in self._cancelled:
            raise RefreshCancelled("refresh cancelled")

    def is_cancelled(self, run_id: str | None) -> bool:
        return bool(run_id and run_id in self._cancelled)


DEFAULT_REFRESH_CANCELLATIONS = RefreshCancellationRegistry()
