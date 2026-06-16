import asyncio
import logging
import sys

from hermes_ble_nodes.qt import BleNode
from qtpy import QtWidgets
import PySide6.QtAsyncio as QtAsyncio  # type: ignore

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    config = BleNode.Config(type="ble_node", user_config=BleNode.Config.UserConfig())
    node = BleNode(config)

    widget = node.widget(node)
    widget.show()

    # with AsyncSlotRunner(debug=True):
    #     loop = asyncio.get_event_loop()
    #     loop.slow_callback_duration = 0.02
    #     sys.exit(app.exec_())
    QtAsyncio.run(handle_sigint=True)
