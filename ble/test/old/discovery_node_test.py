import asyncio

# Setup logging
import logging

from hermes_ble_nodes.qt import BleNode
from hermes_ble_nodes.qt.discovery_node import BleDiscoveryNode

logging.basicConfig(level=logging.INFO)

config = BleDiscoveryNode.Config()


async def main():
    node = BleDiscoveryNode(config=config)
    await node.attempt_init()
    await asyncio.sleep(0.5)
    await node.attempt_deinit()


if __name__ == "__main__":
    asyncio.run(main())
