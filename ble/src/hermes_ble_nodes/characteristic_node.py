"""GATT characteristic node: subscribe to a characteristic and/or write to one.

Notifications on `rx_uuid` come out as `CharacteristicDataPacket`s on the
output link. `BinaryDataPacket`s arriving on the input port are written to
`tx_uuid`, chunked to the negotiated MTU. At least one uuid must be set:

- only `rx_uuid`: notify-only source
- only `tx_uuid`: write-only sink
- both (possibly the same uuid): bidirectional transport

The owning `BleNode` connects/reconnects in the background; this node
(re)subscribes through its connection listeners, so it survives link drops.
Writes may arrive from any thread (typically a Qt widget); they are scheduled
onto the asyncio loop the link lives on.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Literal

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from pydantic import Field, model_validator

from node_hermes_core.datatypes import BinaryDataPacket, GenericDataPacket
from node_hermes_core.generic_node.dependency_manager import NodeDependency
from node_hermes_core.generic_node.generic import AsyncGenericNode
from node_hermes_core.source_sink_node import SourceSinkNode

from .node import BleNode


@dataclass
class CharacteristicDataPacket(BinaryDataPacket):
    characteristic_uuid: str


class BleCharacteristicNode(SourceSinkNode, AsyncGenericNode):
    """Notify and/or write on BLE GATT characteristics: emits each rx_uuid
    notification as a data packet, writes incoming port data to tx_uuid
    (see the module docstring for the three modes).

    The owning BleNode is either injected via the constructor (programmatic
    composition) or referenced by node path in the config (YAML composition) —
    the dependency manager resolves the path and hands the instance to init().
    """

    class Config(SourceSinkNode.Config):
        type: Literal["ble_characteristic_node"] = "ble_characteristic_node"
        rx_uuid: str | None = Field(
            default=None,
            description="Characteristic to subscribe to (device -> host bytes). "
            "Unset: write-only.",
        )
        tx_uuid: str | None = Field(
            default=None,
            description="Characteristic to write input-port bytes to (host -> "
            "device). Unset: notify-only. Same uuid as rx_uuid: single "
            "bidirectional characteristic.",
        )
        write_with_response: bool = Field(
            default=False,
            description="Use write-with-response instead of write-without-response.",
        )
        ble_node: str | None = Field(
            default=None,
            description="Node path of the BleNode that owns the connection (only for "
            "YAML composition; ignored when a BleNode is passed to the constructor)",
        )

        @model_validator(mode="after")
        def _at_least_one_uuid(self):
            if self.rx_uuid is None and self.tx_uuid is None:
                raise ValueError("set rx_uuid (notify), tx_uuid (write), or both")
            return self

    config: Config

    def __init__(self, config: Config, ble_node: BleNode | None = None):
        super().__init__(config)
        self.ble_node = ble_node
        self._warned_no_tx = False
        if ble_node is None:
            if config.ble_node is None:
                raise ValueError(
                    "BleCharacteristicNode needs a BleNode: pass one to the "
                    "constructor or set `ble_node` in the config"
                )
            self.dependency_manager.dependencies.append(
                NodeDependency(name="ble_node", config=config.ble_node, reference=BleNode)
            )

    async def init(self, ble_node: BleNode | None = None):
        super().init()
        if ble_node is not None:
            self.ble_node = ble_node
        assert self.ble_node is not None
        # The loop the link lives on; handle_data() may run on other threads.
        self._loop = asyncio.get_running_loop()
        self._write_lock = asyncio.Lock()
        # Don't require a live connection here (the BleNode connects in the
        # background and may reconnect). Register lifecycle callbacks: subscribe
        # on every (re)connect, drop on disconnect. The node goes ACTIVE
        # immediately; data flows once the link is up. Write-only nodes have
        # nothing to subscribe; they just check the link per write.
        if self.config.rx_uuid is not None:
            self.ble_node.add_connection_listener(self._subscribe, self._unsubscribe)

    async def deinit(self):
        ble_node = self.ble_node  # keep the reference: init() may run again
        if self.config.rx_uuid is not None and ble_node is not None and ble_node.is_connected:
            try:
                await ble_node.client.stop_notify(self.config.rx_uuid)  # type: ignore[union-attr]
            except Exception:
                pass

    # ---------------------------------------------------------------- rx

    async def _subscribe(self, client: BleakClient):
        self.log.info(f"Subscribing to characteristic {self.config.rx_uuid}")
        try:
            await client.start_notify(self.config.rx_uuid, self._on_notification)
        except Exception as e:
            # A link can drop in the gap between "connected" and this
            # listener running; the reconnect loop re-fires us, so a failed
            # subscribe is a warning, not a traceback.
            self.log.warning(f"subscribe failed ({e}); waiting for reconnect")

    async def _unsubscribe(self):
        # The link is already gone by the time this fires; start_notify state is
        # dropped with it, so there's nothing to stop. Kept for symmetry/logging.
        self.log.debug(f"Link down; subscription to {self.config.rx_uuid} dropped")

    def _on_notification(self, sender: BleakGATTCharacteristic, data: bytearray):
        self.send_data(
            CharacteristicDataPacket(
                source=self.config.name,
                timestamp=time.time(),
                data=bytes(data),
                characteristic_uuid=str(sender.uuid),
            )
        )

    # ---------------------------------------------------------------- tx

    def handle_data(self, data: GenericDataPacket):
        if not isinstance(data, BinaryDataPacket) or not data.data:
            return
        if self.config.tx_uuid is None:
            if not self._warned_no_tx:
                self._warned_no_tx = True
                self.log.warning("data arrived on the input port but tx_uuid is unset; dropping")
            return
        ble_node = self.ble_node
        if ble_node is None or not ble_node.is_connected:
            return  # nowhere to write; a console retyping is cheaper than a queue
        asyncio.run_coroutine_threadsafe(self._write(data.data), self._loop)

    async def _write(self, payload: bytes):
        ble_node = self.ble_node
        if ble_node is None or ble_node.client is None or not ble_node.is_connected:
            return
        client = ble_node.client
        chunk_size = max(20, (client.mtu_size or 23) - 3)
        try:
            async with self._write_lock:  # keep chunks of concurrent writes ordered
                for offset in range(0, len(payload), chunk_size):
                    await client.write_gatt_char(
                        self.config.tx_uuid,
                        payload[offset : offset + chunk_size],
                        response=self.config.write_with_response,
                    )
        except Exception as e:
            self.log.warning(f"BLE write failed: {e}")
