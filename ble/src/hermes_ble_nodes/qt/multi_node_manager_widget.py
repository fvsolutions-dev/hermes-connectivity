import logging
from typing import List

from qt_ble_discovery_widget import (
    BluetoothDevice,
    BluetoothInfoFields,
    QBLEDiscoveryWidget,
)
from node_hermes_qt.node_manager_widget import NodeManagerWidget
from qtpy import QtCore, QtWidgets

from ..node import BleNode
from .ui.manager_interface import Ui_Form
import asyncio


class QBleMultiManagerWidget(QtWidgets.QWidget, Ui_Form):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.log = logging.getLogger(__name__)

        # Create discovery widget
        self.discovery_widget = QBLEDiscoveryWidget()
        self.discovery_widget.set_columns([BluetoothInfoFields.MERGED_DEVICE_INFO, BluetoothInfoFields.RSSI])
        self.discovery_widget.selection_changed.connect(self.on_discovery_selection_changed)
        self.discovery_group_box.layout().addWidget(self.discovery_widget)
        self.filter_lineedit.textChanged.connect(self.discovery_widget.set_filter)
        self.node_manager_widget = NodeManagerWidget()
        self.devicesGroupBox.layout().addWidget(self.node_manager_widget)

        # Get the header and set resizing modes for each section
        header = self.discovery_widget.viewer_widget.header()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)

        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Interactive)

        # Set size of second column
        header.resizeSection(1, 40)

        # Set up a timer to start the scan after the widget is loaded
        self.post_load_singleshot_timer = QtCore.QTimer()
        self.post_load_singleshot_timer.setSingleShot(True)
        self.post_load_singleshot_timer.timeout.connect(lambda: asyncio.ensure_future(self.on_load()))
        self.post_load_singleshot_timer.start(0)

        # Set up a timer to update the UI
        self.ui_update_timer = QtCore.QTimer()
        self.ui_update_timer.setInterval(500)
        self.ui_update_timer.timeout.connect(self.update_ui)
        self.ui_update_timer.start()

        self.auto_init_checkbox.setChecked(True)

        self.setStyleSheet(
            """:disabled{
            background-color: lightgray;
            color: gray;
            }"""
        )

        self.add_btn.clicked.connect(self.handle_add)

    @property
    def active_nodes(self) -> List[BleNode]:
        return self.node_manager_widget.active_nodes  # type: ignore

    def handle_add(self):
        selected_device = self.discovery_widget.selected_device

        if selected_device is None:
            return

        if selected_device.full_name in self.node_manager_widget.managed_nodes:
            print(f"Node with name {selected_device.full_name} already exists")
            return

        config = BleNode.Config(
            type="ble_node",
            user_config=BleNode.Config.UserConfig(address=selected_device.address),
        )
        config.user_config._ble_discovered_device = selected_device
        config.name = selected_device.full_name

        self.node_manager_widget.add_node(BleNode(config), auto_init=self.auto_init_checkbox.isChecked())

        self.update_enabled_state()

    async def on_load(self):
        await self.discovery_widget.start_scan_with_discovery()

    def on_discovery_selection_changed(self, device: BluetoothDevice):
        self.update_enabled_state()

    def update_ui(self):
        self.node_manager_widget.update_ui()
        self.update_enabled_state()

    def update_enabled_state(self):
        discovery_device = self.discovery_widget.selected_device

        self.add_btn.setEnabled(
            discovery_device is not None and discovery_device.full_name not in self.node_manager_widget.managed_nodes
        )
