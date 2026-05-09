from hermes_ble_nodes.node import BleNode
import asyncio

async def test_ble_node_reception():

    node = BleNode(config=BleNode.Config(name_match="iris-odin-.*"))
    print("Scanning for BLE devices...")
    await node.init()
    print("Connected to BLE device, waiting to receive data...")
    
    # List characteristics
    for service in node.client.services: #type: ignore
        print(f"Service: {service.uuid}")
        for char in service.characteristics:
            print(f"  Characteristic: {char.uuid}, properties: {char.properties}")

    await node.deinit()


if __name__ == "__main__":
    asyncio.run(test_ble_node_reception())