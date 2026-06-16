"""Round-trip tests for UdpStream and TcpStreamClient via localhost loopback."""

from __future__ import annotations

import asyncio
import time

from hermes_socket_nodes import TcpStreamClient, UdpStream
from node_hermes_core.datatypes import BinaryDataPacket
from node_hermes_core.generic_node.port import CallbackPort, DirectPort


async def _free_port(family: int = 0) -> int:
    """Bind to ephemeral port, close, return the number — racy but fine for tests."""
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM if family else socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


async def test_udp_stream_round_trip():
    port = await _free_port(family=0)

    # Bind a "device" UDP socket the node will talk to.
    loop = asyncio.get_running_loop()
    received_at_device: list[bytes] = []

    class _DeviceProto(asyncio.DatagramProtocol):
        def datagram_received(self, data, addr):
            received_at_device.append(data)
            # Echo back so the node sees something on its rx pump.
            self.transport.sendto(b"reply:" + data, addr)  # type: ignore[attr-defined]

        def connection_made(self, transport):
            self.transport = transport

    device_transport, _ = await loop.create_datagram_endpoint(
        _DeviceProto, local_addr=("127.0.0.1", port)
    )

    received_at_node: list[bytes] = []
    node = UdpStream(UdpStream.Config(uri=f"udp://127.0.0.1:{port}", source=DirectPort.Config()))
    node.base_link.add_target(
        CallbackPort(config=CallbackPort.Config(), callback=lambda p: received_at_node.append(p.data))
    )

    await node.attempt_init()
    try:
        node.handle_data(BinaryDataPacket(source="t", timestamp=time.time(), data=b"hello"))
        for _ in range(50):
            if received_at_node:
                break
            await asyncio.sleep(0.01)
    finally:
        await node.recursive_deinit()
        device_transport.close()

    assert received_at_device == [b"hello"]
    assert received_at_node == [b"reply:hello"]


async def test_tcp_stream_client_round_trip():
    port = await _free_port(family=1)

    received_at_server: list[bytes] = []

    async def _serve(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        data = await reader.read(64)
        received_at_server.append(data)
        writer.write(b"echo:" + data)
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(_serve, "127.0.0.1", port)

    received_at_client: list[bytes] = []
    node = TcpStreamClient(TcpStreamClient.Config(
        host="127.0.0.1", port=port, source=DirectPort.Config(),
    ))
    node.base_link.add_target(
        CallbackPort(config=CallbackPort.Config(), callback=lambda p: received_at_client.append(p.data))
    )

    await node.attempt_init()
    try:
        node.handle_data(BinaryDataPacket(source="t", timestamp=time.time(), data=b"hi"))
        for _ in range(50):
            if received_at_client:
                break
            await asyncio.sleep(0.01)
    finally:
        await node.recursive_deinit()
        server.close()
        await server.wait_closed()

    assert received_at_server == [b"hi"]
    # Server echoed b"echo:hi"; the client may receive it in one or more chunks.
    assert b"".join(received_at_client) == b"echo:hi"
