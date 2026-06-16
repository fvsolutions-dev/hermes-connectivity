"""Lightweight TX/RX byte counter with smoothed rate calculation.

Lifted from the old `hermes-stream-nodes`; kept self-contained so the UART
node can expose a rate via `info_string` without any Hermes data-flow
plumbing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class StreamStatistics:
    tx_bytes: int = 0
    rx_bytes: int = 0
    tx_rate: float = 0.0  # bits per second
    rx_rate: float = 0.0  # bits per second

    def to_dict(self) -> dict:
        return {
            "tx_bytes": self.tx_bytes,
            "rx_bytes": self.rx_bytes,
            "tx_rate": self.tx_rate,
            "rx_rate": self.rx_rate,
        }


class StreamStatisticsManager:
    """Counts TX/RX bytes and reports a smoothed rate.

    `register_tx_bytes` / `register_rx_bytes` are called from the I/O paths;
    `get_rates()` returns a snapshot, recomputing the smoothed rate at most
    once every 100 ms.
    """

    filter_factor = 0.1  # exponential smoothing on the rate samples

    def __init__(self):
        self.tx_bytes = 0
        self.rx_bytes = 0
        self._last_update = time.time()
        self._last_stats = StreamStatistics()

    def register_tx_bytes(self, n: int) -> None:
        self.tx_bytes += n

    def register_rx_bytes(self, n: int) -> None:
        self.rx_bytes += n

    def get_rates(self) -> StreamStatistics:
        now = time.time()
        elapsed = now - self._last_update
        if elapsed < 0.1:
            return self._last_stats

        tx_rate = (self.tx_bytes - self._last_stats.tx_bytes) * 8 / elapsed
        rx_rate = (self.rx_bytes - self._last_stats.rx_bytes) * 8 / elapsed

        self._last_stats = StreamStatistics(
            tx_bytes=self.tx_bytes,
            rx_bytes=self.rx_bytes,
            tx_rate=self.filter_factor * self._last_stats.tx_rate + (1 - self.filter_factor) * tx_rate,
            rx_rate=self.filter_factor * self._last_stats.rx_rate + (1 - self.filter_factor) * rx_rate,
        )
        self._last_update = now
        return self._last_stats
