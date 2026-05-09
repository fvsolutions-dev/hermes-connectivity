# Hermes connectivity

Hermes nodes that talk to the physical link layer.

## Packages

- **`ble/`** (`hermes-ble-nodes`) — BLE advertising scanner, GATT client, characteristic node.
- **`uart/`** (`hermes-uart-nodes`) — Async serial-port node (powered by `aioserial`).
- **`sockets/`** (`hermes-socket-nodes`) — UDP / TCP nodes.
- **`framing/`** (`hermes-framing-nodes`) — Byte-stream framing nodes (COBS, burst-link).

## Layout

This is a `uv` workspace; each subdirectory is an independently installable package. From the repo root:

```sh
uv sync           # install all packages
uv run pytest     # run all tests
```

Each package is built with `hatchling` + `hatch-vcs` and is meant to be published to PyPI on its own.
