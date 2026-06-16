import asyncio
import logging
import sys

import PySide6.QtAsyncio as QtAsyncio  # type: ignore
from qtpy import QtWidgets

from hermes_ble_nodes.qt import QBleMultiManagerWidget

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("bleak").setLevel(logging.INFO)
logging.getLogger("ble_discovery_widget").setLevel(logging.INFO)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = QBleMultiManagerWidget()
    widget.show()

    QtAsyncio.run(handle_sigint=True)
