"""Model a worker retaining a reference after request teardown."""

from typing import Dict, Optional


class Worker:
    def __init__(self, *, reset_on_shutdown: bool):
        self.reset_on_shutdown = reset_on_shutdown
        self.request_heap: Dict[int, str] = {}
        self.cached_handle: Optional[int] = None

    def interrupted_request(self) -> None:
        self.request_heap[1] = "request-owned state"
        self.cached_handle = 1
        # The operation was interrupted before it cleared its cached handle.
        if self.reset_on_shutdown:
            self.cached_handle = None
        self.request_heap.clear()

    def next_request_before_initialization(self) -> str:
        if self.cached_handle is None:
            return "NO_STALE_HANDLE"
        if self.cached_handle not in self.request_heap:
            return "STALE_HANDLE"
        return "LIVE_HANDLE"


def main() -> None:
    for reset_on_shutdown in (False, True):
        worker = Worker(reset_on_shutdown=reset_on_shutdown)
        worker.interrupted_request()
        result = worker.next_request_before_initialization()
        print(f"reset_on_shutdown={reset_on_shutdown}: {result}")


if __name__ == "__main__":
    main()
