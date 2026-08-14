import time


class Timer:
    """High-resolution monotonic clock used for all reaction-time timing."""

    @staticmethod
    def now_ns() -> int:
        return time.monotonic_ns()

    @staticmethod
    def now_ms() -> int:
        return time.monotonic_ns() // 1_000_000

    @staticmethod
    def elapsed_ms(start_ns: int, end_ns: int) -> float:
        return (end_ns - start_ns) / 1_000_000.0
