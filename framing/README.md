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

Decoder buffers partial frames between `handle_data` calls; CRC failures
emit a log warning and the bad frame is dropped (the buffer is not
poisoned). Wire format mirrors
[`burst-link-protocol`](./burst-link-protocol)'s `BurstInterfacePy`; the
submodule is the canonical reference (and offers a C-extension fast path
for hosts that can compile it).
