"""BURST-link protocol framing nodes.

Wraps the canonical `burst_link_protocol.BurstInterfaceC` (C-extension via
nanobind) as Hermes `SourceSinkNode`s:

- ``BurstLinkNode`` — decoder. Bytes (`BinaryDataPacket`) in, decoded
  packets (`BinaryDataPacket`) out, one emit per successfully-framed
  packet. Stream prefixes are buffered inside the underlying
  `BurstInterfaceC` instance until the next ``\\x00`` terminator arrives.
- ``BurstLinkEncoder`` — encoder. Packets (`BinaryDataPacket`) in,
  framed bytes (`BinaryDataPacket`) out.

Both nodes expose a `statistics` view that reads back the C interface's
internal counters (`bytes_handled`, `bytes_processed`, `packets_processed`,
`crc_errors`, `overflow_errors`, `decode_errors`); surface them via
`info_string` for live debugging.
"""

from __future__ import annotations

import time
from typing import Literal

from burst_link_protocol import BurstInterfaceC
from node_hermes_core.datatypes import BinaryDataPacket, GenericDataPacket
from node_hermes_core.source_sink_node import SourceSinkNode


def _stats_str(interface: BurstInterfaceC) -> str:
    return (
        f"bytes {interface.bytes_handled}/{interface.bytes_processed} "
        f"packets {interface.packets_processed} "
        f"errors crc={interface.crc_errors} "
        f"overflow={interface.overflow_errors} "
        f"decode={interface.decode_errors}"
    )


class BurstLinkNode(SourceSinkNode):
    """Decoder: framed bytes in -> decoded packets out.

    `BurstInterfaceC.decode()` is stateful — it buffers any partial
    trailing frame internally, so successive `handle_data` calls compose
    correctly. CRC failures don't raise; they bump the `crc_errors`
    counter and the bad frame is dropped.
    """

    class Config(SourceSinkNode.Config):
        type: Literal["burst_link_decoder"] = "burst_link_decoder"

    config: Config

    def __init__(self, config: Config):
        super().__init__(config)
        self.interface = BurstInterfaceC()

    def init(self):
        super().init()
        # Reset by replacing the interface — clears the partial-frame buffer
        # and zeroes the counters in one shot.
        self.interface = BurstInterfaceC()

    def handle_data(self, data: GenericDataPacket):
        if not isinstance(data, BinaryDataPacket):
            return
        try:
            packets = self.interface.decode(data.data, fail_on_crc_error=False)
        except Exception as exc:
            self.log.warning(f"burst-link decode error: {exc}")
            return
        ts = time.time()
        for payload in packets:
            self.send_data(BinaryDataPacket(source=self.name, timestamp=ts, data=payload))

    @property
    def info_string(self) -> str:
        return _stats_str(self.interface)


class BurstLinkEncoder(SourceSinkNode):
    """Encoder: payload packets in -> framed bytes out (one BinaryDataPacket per encoded frame)."""

    class Config(SourceSinkNode.Config):
        type: Literal["burst_link_encoder"] = "burst_link_encoder"

    config: Config

    def __init__(self, config: Config):
        super().__init__(config)
        self.interface = BurstInterfaceC()

    def init(self):
        super().init()
        self.interface = BurstInterfaceC()

    def handle_data(self, data: GenericDataPacket):
        if not isinstance(data, BinaryDataPacket):
            return
        framed = self.interface.encode([data.data])
        self.send_data(BinaryDataPacket(source=self.name, timestamp=time.time(), data=framed))

    @property
    def info_string(self) -> str:
        return _stats_str(self.interface)
