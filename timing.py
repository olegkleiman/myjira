"""Lightweight phase timing for understanding where a run spends its time."""

import time
from contextlib import contextmanager
from typing import Dict


class Timings:
    """Records how long each named phase of a run took, in the order measured."""

    def __init__(self):
        self.durations: Dict[str, float] = {}

    @contextmanager
    def measure(self, label: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.durations[label] = elapsed
            print(f"[TIMING] {label}: {elapsed:.2f}s")

    def print_summary(self) -> None:
        if not self.durations:
            return
        total = sum(self.durations.values())
        print("\n" + "=" * 80)
        print("TIMING SUMMARY")
        print("=" * 80)
        for label, elapsed in self.durations.items():
            pct = (elapsed / total * 100) if total else 0
            print(f"  {label:<40} {elapsed:>8.2f}s  ({pct:5.1f}%)")
        print(f"  {'TOTAL':<40} {total:>8.2f}s")
        print("=" * 80)
