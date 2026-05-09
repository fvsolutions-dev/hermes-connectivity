"""BURST-link protocol framing nodes.

The BURST wire format is COBS-encoded ``payload + CRC16/IBM-3740`` followed
by a ``\\x00`` terminator. This module exposes two `SourceSinkNode`s that
sit between a raw byte transport and a packet consumer:

- ``BurstLinkNode`` — decoder. Bytes (`BinaryDataPacket`) in, decoded
  packets (`BinaryDataPacket`) out, one emit per successfully-framed
  packet. Stream prefixes are buffered until the next ``\\x00``.
- ``BurstLinkEncoder`` — encoder. Packets (`BinaryDataPacket`) in, framed
  bytes (`BinaryDataPacket`) out.

Wire format mirrors `burst_link_protocol.BurstInterfacePy` exactly; the
canonical implementation lives in the burst-link-protocol submodule.
"""

from __future__ import annotations

import time
from typing import Literal

from cobs import cobs
from crc import Calculator, Crc16
from node_hermes_core.datatypes import BinaryDataPacket, GenericDataPacket
from node_hermes_core.source_sink_node import SourceSinkNode

_CRC = Calculator(Crc16.IBM_3740)  # type: ignore


def _crc16(data: bytes) -> bytes:
    return _CRC.checksum(data).to_bytes(2, "big")


def encode_packet(payload: bytes) -> bytes:
    """Encode one payload as a BURST frame (COBS + CRC16 + 0x00 terminator)."""
    return cobs.encode(payload + _crc16(payload)) + b"\x00"


def decode_packet(frame_without_terminator: bytes) -> bytes:
    """Decode one COBS-encoded frame (no terminator). Raises ``ValueError`` on CRC failure."""
    decoded = cobs.decode(frame_without_terminator)
    if _crc16(decoded[:-2]) != decoded[-2:]:
        raise ValueError("CRC mismatch")
    return decoded[:-2]


class BurstLinkNode(SourceSinkNode):
    """Decoder: framed bytes in -> decoded packets out.

    Multiple frames in one input chunk are split on ``\\x00`` boundaries;
    a partial trailing frame is buffered until its terminator arrives.
    Frames that fail CRC are dropped with a warning — the buffer is not
    poisoned, decoding resumes at the next terminator.
    """

    class Config(SourceSinkNode.Config):
        type: Literal["burst_link_decoder"] = "burst_link_decoder"

    config: Config
    _buffer: bytes = b""

    def init(self):
        super().init()
        self._buffer = b""

    def handle_data(self, data: GenericDataPacket):
        if not isinstance(data, BinaryDataPacket):
            return
        self._buffer += data.data
        # Anything followed by a 0x00 is a complete frame; the trailing
        # element after split is whatever is still mid-frame.
        parts = self._buffer.split(b"\x00")
        self._buffer = parts.pop()
        ts = time.time()
        for raw in parts:
            if not raw:
                continue
            try:
                payload = decode_packet(raw)
            except (ValueError, cobs.DecodeError) as exc:
                self.log.warning(f"burst-link decode error: {exc}")
                continue
            self.send_data(BinaryDataPacket(source=self.name, timestamp=ts, data=payload))


class BurstLinkEncoder(SourceSinkNode):
    """Encoder: payload packets in -> framed bytes out (one BinaryDataPacket per encoded frame)."""

    class Config(SourceSinkNode.Config):
        type: Literal["burst_link_encoder"] = "burst_link_encoder"

    config: Config

    def handle_data(self, data: GenericDataPacket):
        if not isinstance(data, BinaryDataPacket):
            return
        framed = encode_packet(data.data)
        self.send_data(BinaryDataPacket(source=self.name, timestamp=time.time(), data=framed))
