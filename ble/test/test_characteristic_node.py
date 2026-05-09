import asyncio
import logging

from hermes_ble_nodes.characteristic_node import BleCharacteristicNode
from hermes_ble_nodes.node import BleNode
from node_hermes_core.generic_node.port import CallbackPort

DEVICE_NAME_REGEX = "iris-odin-.*"
CHARACTERISTIC_UUID = "0000ee06-0000-1000-8000-00805f9b34fb"


async def test_ble_characteristic_node_reception():
    ble_node = BleNode(config=BleNode.Config(name_match=DEVICE_NAME_REGEX))

    # Log all characteristics
    # ble_node.dump_characteristics()

    char_node = BleCharacteristicNode(
        ble_node=ble_node,
        config=BleCharacteristicNode.Config(characteristic_uuid=CHARACTERISTIC_UUID),
    )

    receive_count = 0

    def on_data(packet):
        nonlocal receive_count
        print(f"notif: {packet.characteristic_uuid} ({len(packet.data)} bytes) {packet.data.hex()}")
        receive_count += 1

    port = CallbackPort(config=CallbackPort.Config(), callback=on_data)
    char_node.base_link.add_target(port)

    try:
        await ble_node.init()
        await char_node.init()
        await asyncio.sleep(5)

    finally:
        await char_node.deinit()
        await ble_node.deinit()

    assert receive_count > 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_ble_characteristic_node_reception())
