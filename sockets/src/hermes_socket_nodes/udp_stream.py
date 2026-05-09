"""UDP datagram transport as a Hermes node."""

from __future__ import annotations

import asyncio
import time
import urllib.parse
from typing import Literal

from node_hermes_core.datatypes import BinaryDataPacket, GenericDataPacket
from node_hermes_core.source_sink_node import SourceSinkNode


class _UdpProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_datagram):
        self._on_datagram = on_datagram

    def connection_made(self, transport: asyncio.DatagramTransport):  # type: ignore[override]
        self.transport = transport

    def datagram_received(self, data: bytes, addr) -> None:
        self._on_datagram(data, addr)

    def error_received(self, exc) -> None:  # noqa: D401
        # Silenced; surface via the parent node's logger if needed.
        pass


class UdpStream(SourceSinkNode):
    """UDP transport: each datagram in/out is one `BinaryDataPacket`.

    Configured with `udp://host:port`. The node opens a connected datagram
    endpoint pointed at that remote, so:

    - `BinaryDataPacket`s arriving on the input port are sent as UDP
      datagrams to the configured remote.
    - Datagrams arriving on the underlying socket are emitted on the output
      Link as `BinaryDataPacket`s.

    Each Hermes packet maps 1:1 to one datagram — UDP framing is preserved.
    """

    class Config(SourceSinkNode.Config):
        type: Literal["udp_stream"] = "udp_stream"
        uri: str

    config: Config
    transport: asyncio.DatagramTransport | None = None
    protocol: _UdpProtocol | None = None

    async def init(self):
        super().init()
        parsed = urllib.parse.urlparse(self.config.uri)
        if parsed.scheme != "udp":
            raise ValueError(f"UdpStream uri must use udp:// scheme, got {self.config.uri!r}")
        if not parsed.hostname or not parsed.port:
            raise ValueError(f"UdpStream uri must include host and port, got {self.config.uri!r}")

        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: _UdpProtocol(self._on_datagram),
            remote_addr=(parsed.hostname, parsed.port),
        )
        self.transport = transport
        self.protocol = protocol

    async def deinit(self):
        if self.transport is not None:
            self.transport.close()
            self.transport = None
        self.protocol = None

    def handle_data(self, data: GenericDataPacket):
        if self.transport is None or not isinstance(data, BinaryDataPacket):
            return
        self.transport.sendto(data.data)

    def _on_datagram(self, data: bytes, addr) -> None:
        self.send_data(BinaryDataPacket(source=self.name, timestamp=time.time(), data=data))
