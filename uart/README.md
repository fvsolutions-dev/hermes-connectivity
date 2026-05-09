# hermes-uart-nodes

Async serial-port nodes for the Hermes data flow.

## `SerialStream`

A bidirectional `SourceSinkNode` wrapping `aioserial.AioSerial`:

- `BinaryDataPacket`s arriving on the input port are written to the wire.
- A background RX pump reads bursts and emits each as a `BinaryDataPacket`
  on the output Link (batched up to `max_chunk` bytes per packet).
- TX/RX byte totals + smoothed bit rate are tracked internally and surfaced
  through `info_string` only — the data flow stays single-typed.

Discovery helpers `SerialPortInfo` and `get_serial_ports(pid=…, vid=…)`
expose `serial.tools.list_ports` for finding the right device.
