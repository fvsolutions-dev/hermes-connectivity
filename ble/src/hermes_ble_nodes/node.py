import asyncio
from typing import Literal

from bleak import BleakClient
from pydantic import Field

from node_hermes_core.generic_node.generic import AsyncGenericNode

from .discovery import BleDiscovery


class BleNode(AsyncGenericNode):
    class Config(AsyncGenericNode.Config, BleDiscovery.Config):
        type: Literal["ble_node"] = "ble_node"
        connection_timeout: float = Field(description="The timeout for connection", default=5)

    config: Config
    client: BleakClient | None = None

    async def init(self):
        discovery = BleDiscovery(self.config, log=self.log)
        device, scanner = await discovery.scan()
        try:
            self.log.info(f"Connecting to BLE device {device}")
            self.client = BleakClient(device, disconnected_callback=self.disconnected_callback)
            await asyncio.wait_for(self.client.connect(), timeout=self.config.connection_timeout)
            self.log.info("Connected to BLE device")
        finally:
            await scanner.stop()

    async def deinit(self):
        if self.client is not None:
            await self.client.disconnect()
            self.client = None

    def dump_characteristics(self):
        if self.client is None:
            self.log.warning("Not connected to any BLE device")
            return
        
        for service in self.client.services:  # type: ignore
            print(f"Service: {service.uuid}")
            for char in service.characteristics:
                print(f"  Characteristic: {char.uuid}, properties: {char.properties}")

    def disconnected_callback(self, client: BleakClient):
        self.log.info("Disconnected from BLE device")
        asyncio.create_task(self.attempt_deinit())

    def __str__(self):
        return f"{self.config.name}"

    @property
    def widget(self):
        from .qt.widget import BleWidget

        return BleWidget
