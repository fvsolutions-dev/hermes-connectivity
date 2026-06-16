import logging
from node_hermes_qt.connection_widget import QConnectionDisplayWidget
from qt_ble_discovery_widget import QBLEDiscoveryWidget, BluetoothInfoFields, BluetoothDevice
from qtpy import QtCore, QtWidgets

from .ui.interface import Ui_Form
from ..node import BleNode
from node_hermes_qt.nodes.generic_qt_node import GenericNodeWidget
import asyncio

class BleWidget(GenericNodeWidget, Ui_Form):
    def __init__(self, node: "BleNode", parent=None):
        super().__init__(node)
        self.setupUi(self)
        self.component = node

        self.log = logging.getLogger(__name__)

        # Create connection widget
        self.connect_widget = QConnectionDisplayWidget(self.component)
        self.connectLayout.addWidget(self.connect_widget)
        self.connect_widget.state_update_signal.connect(self.update_ui)

        # Create discovery widget
        self.discovery_widget = QBLEDiscoveryWidget()
        self.discovery_widget.set_columns([BluetoothInfoFields.MERGED_DEVICE_INFO])
        self.discovery_group_box.layout().addWidget(self.discovery_widget)
        self.discovery_widget.selection_changed.connect(self.on_discovery_selection_changed)

        # Set up a timer to start the scan after the widget is loaded
        self.post_load_singleshot_timer = QtCore.QTimer()
        self.post_load_singleshot_timer.setSingleShot(True)
        self.post_load_singleshot_timer.timeout.connect(lambda: asyncio.ensure_future(self.on_load()))
        self.post_load_singleshot_timer.start(0)

        # Load the config
        self.from_config(self.component.config)

        # Connect the on change signals
        self.addressLineEdit.textChanged.connect(self.on_manual_change)
        self.setStyleSheet(
            """:disabled{
            background-color: lightgray;
            color: gray;
            }"""
        )

    async def on_load(self):
        await self.discovery_widget.start_scan_with_discovery()

    def on_discovery_selection_changed(self, device: BluetoothDevice):
        self.component.config.user_config._ble_discovered_device = device
        self.component.config.user_config.address = device.address

        self.from_config(self.component.config)
        self.update_ui()

    def on_manual_change(self):
        self.component.config.user_config._ble_discovered_device = None
        self.to_config(self.component.config)
        self.update_ui()

    def from_config(self, config: "BleNode.Config"):
        self.addressLineEdit.blockSignals(True)
        self.addressLineEdit.setText(config.user_config.address)
        self.addressLineEdit.blockSignals(False)

    def to_config(self, cfg: "BleNode.Config"):
        cfg.user_config.address = self.addressLineEdit.text()

    def update_ui(self):
        discovery_based = self.component.config.user_config._ble_discovered_device is not None
        self.addressLineEdit.setStyleSheet("background-color: lightblue" if discovery_based else "")

        # If connected, disable the address line edit and selection widget
        is_connected = self.component.state not in [
            self.component.State.STOPPED,
            self.component.State.ERROR,
            self.component.State.IDLE,
        ]
        self.addressLineEdit.setEnabled(not is_connected)
        self.discovery_widget.setEnabled(not is_connected)
