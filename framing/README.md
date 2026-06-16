# hermes-framing-nodes

Hermes nodes for byte-stream framing protocols. Each node sits between a
raw-byte transport (`SerialStream`, BLE, …) and a packet-oriented consumer
(`HermesErosGatewayNode`, `OdinStreamNode`, …).

## `BurstLinkNode` / `BurstLinkEncoder`

BURST-link wire format: each payload is wrapped as
``COBS(payload + CRC16/IBM-3740) + 0x00``.

| node | direction |
| --- | --- |
| `BurstLinkNode` (decoder) | framed bytes in → decoded packets out |
| `BurstLinkEncoder` | payload packets in → framed bytes out |

Both nodes use [`burst-link-protocol`](./burst-link-protocol)'s
`BurstInterfaceC` (nanobind C extension) under the hood — the canonical
implementation, no duplicate logic. The C extension is built when this
package is installed; pre-built wheels are also published from
burst-link-protocol's CI.

The decoder buffers partial frames between `handle_data` calls (state
held inside `BurstInterfaceC`); CRC failures bump the `crc_errors`
counter and the bad frame is silently dropped. Both nodes expose live
counter strings via `info_string`.
