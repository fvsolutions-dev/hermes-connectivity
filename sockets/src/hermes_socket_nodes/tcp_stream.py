"""TCP stream transport as a Hermes node (client)."""

from __future__ import annotations

import asyncio
import time
from typing import Literal

from node_hermes_core.datatypes import BinaryDataPacket, GenericDataPacket
from node_hermes_core.source_sink_node import SourceSinkNode
from pydantic import Field


class TcpStreamClient(SourceSinkNode):
    """TCP client transport: bytes through `BinaryDataPacket`s in both directions.

    Connects to ``host:port`` on init. Outgoing `BinaryDataPacket` payloads
    are written to the socket as-is (no framing — pair with a framing node
    such as `BurstLinkNode` if you need packet boundaries). Incoming bytes
    are read in `max_chunk` bursts and emitted as `BinaryDataPacket`s.
    """

    class Config(SourceSinkNode.Config):
        type: Literal["tcp_stream_client"] = "tcp_stream_client"
        host: str
        port: int
        max_chunk: int = Field(
            default=4096,
            description="Maximum bytes per emitted BinaryDataPacket.",
        )

    config: Config
    reader: asyncio.StreamReader | None = None
    writer: asyncio.StreamWriter | None = None
    _rx_task: asyncio.Task | None = None

    async def init(self):
        super().init()
        self.reader, self.writer = await asyncio.open_connection(
            self.config.host, self.config.port
        )
        self._rx_task = asyncio.create_task(self._pump_rx())

    async def deinit(self):
        if self._rx_task is not None:
            self._rx_task.cancel()
            self._rx_task = None
        if self.writer is not None:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except (ConnectionError, OSError):
                pass
            self.writer = None
        self.reader = None

    def handle_data(self, data: GenericDataPacket):
        if self.writer is None or not isinstance(data, BinaryDataPacket):
            return
        self.writer.write(data.data)
        # `drain()` is the right thing to await but we're in a sync handle_data;
        # schedule the drain so back-pressure still gets observed eventually.
        asyncio.create_task(self._drain())

    async def _drain(self) -> None:
        if self.writer is not None:
            try:
                await self.writer.drain()
            except (ConnectionError, OSError):
                pass

    async def _pump_rx(self) -> None:
        assert self.reader is not None
        try:
            while True:
                chunk = await self.reader.read(self.config.max_chunk)
                if not chunk:
                    # Peer closed.
                    return
                self.send_data(
                    BinaryDataPacket(source=self.name, timestamp=time.time(), data=chunk)
                )
        except asyncio.CancelledError:
            return
