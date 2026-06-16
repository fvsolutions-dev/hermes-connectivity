import time
from dataclasses import dataclass
from typing import Literal

from bleak.backends.characteristic import BleakGATTCharacteristic
from pydantic import Field

from node_hermes_core.datatypes import BinaryDataPacket
from node_hermes_core.generic_node.dependency_manager import NodeDependency
from node_hermes_core.generic_node.generic import AsyncGenericNode
from node_hermes_core.source_sink_node import SourceNode

from .node import BleNode


@dataclass
class CharacteristicDataPacket(BinaryDataPacket):
    characteristic_uuid: str


class BleCharacteristicNode(SourceNode, AsyncGenericNode):
    """Source node that subscribes to a BLE GATT characteristic and emits each notification as a binary data packet.

    The owning BleNode is either injected via the constructor (programmatic
    composition) or referenced by node path in the config (YAML composition) —
    the dependency manager resolves the path and hands the instance to init().
    """

    class Config(SourceNode.Config):
        type: Literal["ble_characteristic_node"] = "ble_characteristic_node"
        characteristic_uuid: str = Field(description="UUID of the characteristic to subscribe to")
        ble_node: str | None = Field(
            default=None,
            description="Node path of the BleNode that owns the connection (only for YAML composition; ignored when a BleNode is passed to the constructor)",
        )

    config: Config

    def __init__(self, config: Config, ble_node: BleNode | None = None):
        super().__init__(config)
        self.ble_node = ble_node
        if ble_node is None:
            if config.ble_node is None:
                raise ValueError(
                    "BleCharacteristicNode needs a BleNode: pass one to the "
                    "constructor or set `ble_node` in the config"
                )
            self.dependency_manager.dependencies.append(
                NodeDependency(name="ble_node", config=self.config.ble_node, reference=BleNode)
            )

    async def init(self, ble_node: BleNode | None = None):
        if ble_node is not None:
            self.ble_node = ble_node
        assert self.ble_node is not None
        # Don't require a live connection here (the BleNode connects in the
        # background and may reconnect). Register lifecycle callbacks: subscribe
        # on every (re)connect, drop on disconnect. The node goes ACTIVE
        # immediately; data flows once the link is up.
        self.ble_node.add_connection_listener(self._subscribe, self._unsubscribe)

    async def _subscribe(self, client):
        self.log.info(f"Subscribing to characteristic {self.config.characteristic_uuid}")
        await client.start_notify(self.config.characteristic_uuid, self._on_notification)

    async def _unsubscribe(self):
        # The link is already gone by the time this fires; start_notify state is
        # dropped with it, so there's nothing to stop. Kept for symmetry/logging.
        self.log.debug(f"Link down; subscription to {self.config.characteristic_uuid} dropped")

    async def deinit(self):
        if self.ble_node is None:
            return
        if self.ble_node.client is not None and self.ble_node.client.is_connected:
            try:
                await self.ble_node.client.stop_notify(self.config.characteristic_uuid)
            except Exception:
                pass

    def _on_notification(self, sender: BleakGATTCharacteristic, data: bytearray):
        self.send_data(
            CharacteristicDataPacket(
                source=self.config.name,
                timestamp=time.time(),
                data=bytes(data),
                characteristic_uuid=str(sender.uuid),
            )
        )

    def get_data(self) -> None:
        return None
