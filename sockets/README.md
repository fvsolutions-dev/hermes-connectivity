# hermes-socket-nodes

Hermes nodes for Berkeley socket transports — UDP, TCP. WebSocket lives in
`hermes-web-nodes`, not here.

| node | role |
| --- | --- |
| `UdpStream` | bidirectional UDP datagram transport (`udp://host:port`). One `BinaryDataPacket` per datagram in both directions; UDP framing is preserved 1:1. |
| `TcpStreamClient` | bidirectional TCP byte stream (`host`, `port`). Writes go to the socket as-is; reads emit a `BinaryDataPacket` per burst (up to `max_chunk` bytes). Pair with a framing node (e.g. `BurstLinkNode`) if you need packet boundaries. |

Both wrap `asyncio` primitives (datagram endpoint / stream connection) as a
`SourceSinkNode`, so they slot into the same wiring patterns as `SerialStream`
and the BLE nodes.
