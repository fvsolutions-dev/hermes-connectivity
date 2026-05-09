import time
from dataclasses import dataclass
from typing import Literal

from bleak.backends.characteristic import BleakGATTCharacteristic
from pydantic import Field

from node_hermes_core.datatypes import BinaryDataPacket
from node_hermes_core.generic_node.generic import AsyncGenericNode
from node_hermes_core.source_sink_node import SourceNode

from .node import BleNode


@dataclass
class CharacteristicDataPacket(BinaryDataPacket):
    characteristic_uuid: str


class BleCharacteristicNode(SourceNode, AsyncGenericNode):
    """Source node that subscribes to a BLE GATT characteristic and emits each notification as a binary data packet."""

    class Config(SourceNode.Config):
        type: Literal["ble_characteristic_node"] = "ble_characteristic_node"
        characteristic_uuid: str = Field(description="UUID of the characteristic to subscribe to")

    config: Config

    def __init__(self, ble_node: BleNode, config: Config):
        super().__init__(config)
        self.ble_node = ble_node

    async def init(self):
        if self.ble_node.client is None or not self.ble_node.client.is_connected:
            raise RuntimeError(f"BleNode {self.ble_node} is not connected")

        self.log.info(f"Subscribing to characteristic {self.config.characteristic_uuid}")
        await self.ble_node.client.start_notify(self.config.characteristic_uuid, self._on_notification)

    async def deinit(self):
        if self.ble_node.client is not None and self.ble_node.client.is_connected:
            await self.ble_node.client.stop_notify(self.config.characteristic_uuid)

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
