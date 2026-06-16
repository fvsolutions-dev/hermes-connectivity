from typing import Literal

from node_hermes_core.nodes import GenericNode, AsyncGenericNode
from node_hermes_qt.nodes import GenericQtNode
from node_hermes_qt.nodes.generic_qt_node import GenericNodeWidget

from hermes_ble_nodes.node import BleNode

import logging
from typing import List

from qt_ble_discovery_widget import QBLEDiscoveryWidget, BluetoothDevice, BluetoothInfoFields
from node_hermes_qt.node_manager_widget import NodeManagerWidget
from qtpy import QtCore, QtWidgets

from .ui.manager_interface import Ui_Form


class BleDiscoveryNodeWidget(GenericNodeWidget, Ui_Form):
    def __init__(self, node: "BleDiscoveryNode"):
        super().__init__(node)
        self.setupUi(self)

        self.log = logging.getLogger(__name__)

        # Create discovery widget
        self.discovery_widget = QBLEDiscoveryWidget()
        self.discovery_widget.set_columns([BluetoothInfoFields.MERGED_DEVICE_INFO])
        self.discovery_widget.selection_changed.connect(self.on_discovery_selection_changed)
        self.discovery_group_box.layout().addWidget(self.discovery_widget)

        self.node_manager_widget = NodeManagerWidget()
        self.devicesGroupBox.layout().addWidget(self.node_manager_widget)

        # Set up a timer to start the scan after the widget is loaded
        self.post_load_singleshot_timer = QtCore.QTimer()
        self.post_load_singleshot_timer.setSingleShot(True)
        self.post_load_singleshot_timer.timeout.connect(self.on_load)
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


class BleDiscoveryNode(AsyncGenericNode, GenericQtNode):
    class Config(AsyncGenericNode.Config, GenericQtNode.Config):
        type: Literal["ble_discovery_node"] = "ble_discovery_node"

    async def init(self):
        pass

    @property
    def widget(self):
        return BleDiscoveryNodeWidget
