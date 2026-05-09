# hermes-socket-nodes

Hermes nodes for Berkeley socket transports — UDP, TCP, optionally Unix domain.

> **Status:** stub. The package layout, build, and `NODES` registration list are
> in place; concrete nodes (e.g. a `UdpTransportNode`, `TcpTransportNode`)
> still need to be written. Each will typically wrap an `asyncio` datagram /
> stream protocol as a Hermes Source+Sink node.
>
> _Note: WebSocket is not in scope here — it lives in `hermes-web-nodes`._
