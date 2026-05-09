from hermes_ble_nodes.advertising_node import BleAdvertisingNode
from node_hermes_core.generic_node.port import CallbackPort
import asyncio

async def test_ble_advertising_node_reception():

    node = BleAdvertisingNode(config=BleAdvertisingNode.Config(company_id=0xffff, deduplicate=False))

    receive_count = 0
    def on_data(packet):
        nonlocal receive_count
        print(f"payload: device: {packet.device}, rssi: {packet.rssi} {packet.data}")
        receive_count += 1

    port = CallbackPort(config=CallbackPort.Config(), callback=on_data)

    node.base_link.add_target(port)
    await node.init()
    await asyncio.sleep(5)        
    await node.deinit()
    assert receive_count > 0


if __name__ == "__main__":
    asyncio.run(test_ble_advertising_node_reception())