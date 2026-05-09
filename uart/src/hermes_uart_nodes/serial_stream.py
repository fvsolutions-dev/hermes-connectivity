"""Bidirectional serial-port node.

`SerialStream` wraps an `aioserial.AioSerial` device as a Hermes
`SourceSinkNode`:

- `BinaryDataPacket`s arriving on the input port are written to the wire.
- A background `_pump_rx` task reads bursts from the wire and emits each
  burst as a `BinaryDataPacket` on the output Link.

Statistics (TX/RX byte totals, smoothed bit rate) are kept internally and
surfaced through `info_string` only — they don't pollute the data flow.
"""

from __future__ import annotations

import asyncio
import time
from typing import List, Literal

import aioserial
from node_hermes_core.datatypes import BinaryDataPacket, GenericDataPacket
from node_hermes_core.source_sink_node import SourceSinkNode
from pydantic import BaseModel, Field
from serial.tools import list_ports

from .stats import StreamStatisticsManager


class SerialPortInfo(BaseModel):
    port: str
    description: str
    pid: int | None
    vid: int | None
    serial_number: str | None


def get_serial_ports(
    pid: str | int | None = None, vid: str | int | None = None
) -> List[SerialPortInfo]:
    """List attached serial ports, optionally filtered by USB pid / vid."""
    if isinstance(pid, str):
        pid = int(pid, 16)
    if isinstance(vid, str):
        vid = int(vid, 16)

    discovered = []
    for port in list_ports.comports():
        if pid is not None and port.pid != pid:
            continue
        if vid is not None and port.vid != vid:
            continue
        discovered.append(
            SerialPortInfo(
                port=port.device,
                description=port.description,
                pid=port.pid,
                vid=port.vid,
                serial_number=port.serial_number,
            )
        )
    return discovered


class SerialStream(SourceSinkNode):
    class Config(SourceSinkNode.Config):
        type: Literal["serial_stream"] = "serial_stream"
        port: str
        baudrate: int = 115200
        rx_buffer_size: int = 16 * 1024
        tx_buffer_size: int = 16 * 1024
        max_chunk: int = Field(
            default=4096,
            description="Maximum bytes to bundle into a single emitted BinaryDataPacket.",
        )

    config: Config
    serial: aioserial.AioSerial | None = None
    statistics: StreamStatisticsManager | None = None
    _rx_task: asyncio.Task | None = None

    async def init(self):
        self.base_port.reset()
        self.serial = aioserial.AioSerial(port=self.config.port, baudrate=self.config.baudrate)
        # set_buffer_size is only available on the Windows pyserial backend
        # (and pyserial, which AioSerial subclasses). Best-effort.
        try:
            self.serial.set_buffer_size(
                rx_size=self.config.rx_buffer_size, tx_size=self.config.tx_buffer_size
            )
        except (AttributeError, NotImplementedError):
            pass
        self.statistics = StreamStatisticsManager()
        self._rx_task = asyncio.create_task(self._pump_rx())

    async def deinit(self):
        if self._rx_task is not None:
            self._rx_task.cancel()
            self._rx_task = None
        if self.serial is not None:
            self.serial.close()
            self.serial = None
        self.statistics = None

    def handle_data(self, data: GenericDataPacket):
        """Write incoming `BinaryDataPacket` bytes to the serial port."""
        if self.serial is None or not isinstance(data, BinaryDataPacket):
            return
        # `write_async` is a coroutine; schedule it on the running loop.
        asyncio.create_task(self._write(data.data))

    async def _write(self, payload: bytes) -> None:
        assert self.serial is not None
        await self.serial.write_async(payload)
        if self.statistics is not None:
            self.statistics.register_tx_bytes(len(payload))

    async def _pump_rx(self) -> None:
        """Read bursts from the wire and emit each as a `BinaryDataPacket`.

        We `read_async(1)` first to block until at least one byte arrives
        (without burning the loop), then drain whatever else is in the
        buffer up to `max_chunk` bytes so we batch high-rate streams.
        """
        assert self.serial is not None
        try:
            while True:
                first = await self.serial.read_async(1)
                if not first:
                    continue
                pending = min(self.serial.in_waiting, self.config.max_chunk - 1)
                rest = await self.serial.read_async(pending) if pending > 0 else b""
                chunk = first + rest

                if self.statistics is not None:
                    self.statistics.register_rx_bytes(len(chunk))

                self.send_data(
                    BinaryDataPacket(source=self.name, timestamp=time.time(), data=chunk)
                )
        except asyncio.CancelledError:
            return

    @property
    def info_string(self) -> str:
        if self.statistics is None:
            return "(closed)"
        rates = self.statistics.get_rates()
        return f"rx {rates.rx_rate / 1000:.1f} kbps  tx {rates.tx_rate / 1000:.1f} kbps"
