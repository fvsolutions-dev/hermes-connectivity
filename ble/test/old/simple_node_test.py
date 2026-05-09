from hermes_ble_nodes.qt import BleNode
import asyncio

# Setup logging
import logging

logging.basicConfig(level=logging.INFO)

config = BleNode.Config(
    user_config=BleNode.Config.UserConfig(address="10:94:97:23:16:77"),
)


async def main():
    node = BleNode(config=config)
    await node.attempt_init()    
    await asyncio.sleep(0.5)
    await node.attempt_deinit()


if __name__ == "__main__":
    asyncio.run(main())
