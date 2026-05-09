"""Bidirectional smoke test using a pty pair as a fake serial port.

Skipped on platforms without `pty` (i.e. Windows).
"""

from __future__ import annotations

import asyncio
import os
import time

import pytest

try:
    import pty
except ImportError:
    pty = None  # type: ignore

from hermes_uart_nodes import SerialStream
from node_hermes_core.datatypes import BinaryDataPacket
from node_hermes_core.generic_node.port import CallbackPort, DirectPort


pytestmark = pytest.mark.skipif(pty is None, reason="pty unavailable on this platform")


async def test_bidirectional_serial_stream():
    master_fd, slave_fd = pty.openpty()
    slave_path = os.ttyname(slave_fd)

    stream = SerialStream(SerialStream.Config(
        port=slave_path,
        baudrate=115200,
        source=DirectPort.Config(),
    ))

    received: list[BinaryDataPacket] = []
    stream.base_link.add_target(
        CallbackPort(config=CallbackPort.Config(), callback=received.append)
    )

    await stream.attempt_init()
    try:
        # Device -> Hermes
        os.write(master_fd, b"hello-from-fake-device")
        for _ in range(50):
            if received:
                break
            await asyncio.sleep(0.01)
        assert received, "no inbound packet emitted"
        assert b"hello-from-fake-device" in received[0].data

        # Hermes -> device
        stream.handle_data(
            BinaryDataPacket(source="test", timestamp=time.time(), data=b"echo-back")
        )
        for _ in range(50):
            await asyncio.sleep(0.01)
            try:
                buf = os.read(master_fd, 4096)
            except BlockingIOError:
                continue
            if buf:
                assert buf == b"echo-back"
                break
        else:
            pytest.fail("nothing landed on the master side of the pty")
    finally:
        await stream.recursive_deinit()
        os.close(master_fd)
