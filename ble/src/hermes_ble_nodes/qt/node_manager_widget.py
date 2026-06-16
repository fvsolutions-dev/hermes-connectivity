import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from node_hermes_core.nodes import GenericNode, AsyncGenericNode
from node_hermes_core.depencency import NodeDependency  
from qt_custom_treewidget import ColumnNames, TreeItem, TreeviewViewer
from qtpy import QtGui, QtWidgets


class DeviceInfoFields(ColumnNames):
    NAME = "Name"
    STATE = "State"


@dataclass
class ManagedNode:
    node: GenericNode | AsyncGenericNode
    kwargs: Dict[str, Any]

    def __hash__(self):
        return hash(self.node) + hash(str(self.kwargs))
 
    def __eq__(self, other): # type: ignore
        if isinstance(other, GenericNode) or isinstance(other, AsyncGenericNode):
            return self.node == other


class NodeTreeItem(TreeItem):
    def __init__(self, managed_node: ManagedNode):
        super().__init__()
        self.managed_node = managed_node

    def get_text(self, column_type: DeviceInfoFields): # type: ignore
        if column_type == DeviceInfoFields.NAME:
            return str(self.managed_node.node.name)
        if column_type == DeviceInfoFields.STATE:
            return str(self.managed_node.node.state.name)
        else:
            return "Unknown"

    def get_color(self):
        if self.managed_node.node.state == self.managed_node.node.State.ACTIVE:
            return QtGui.QColor("lightgreen")

        elif self.managed_node.node.state == self.managed_node.node.State.ERROR:
            return QtGui.QColor("lightcoral")

        return None


class NodeManagerWidget(QtWidgets.QWidget):
    managed_nodes: Dict[str, ManagedNode]
    node_treeitems: Dict[ManagedNode, NodeTreeItem]

    node_connection_widgets: List[NodeDependency ]  # Dependency managers which are need input to this widget

    def __init__(self, parent=None):
        super().__init__(parent)
        self.managed_nodes = {}
        self.node_treeitems = {}
        self.node_connection_widgets = []

        self.log = logging.getLogger(__name__)
        main_layout = QtWidgets.QVBoxLayout()

        self.init_btn = QtWidgets.QPushButton("Init")
        self.deinit_btn = QtWidgets.QPushButton("Deinit")
        self.remove_btn = QtWidgets.QPushButton("Remove")

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.init_btn)
        button_layout.addWidget(self.deinit_btn)
        button_layout.addWidget(self.remove_btn)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        # Create connected devices viewer
        self.loaded_devices_viewer = TreeviewViewer()
        self.loaded_devices_viewer.set_columns([DeviceInfoFields.NAME, DeviceInfoFields.STATE])
        self.loaded_devices_viewer.itemSelectionChanged.connect(self.update_enabled_state)
        main_layout.addWidget(self.loaded_devices_viewer)

        self.setStyleSheet(
            """:disabled{
            background-color: lightgray;
            color: gray;
            }"""
        )

        self.init_btn.clicked.connect(self.handle_init)
        self.deinit_btn.clicked.connect(self.handle_deinit)
        self.remove_btn.clicked.connect(self.handle_remove)

    def register_dependency(self, target_dependency_manager: NodeDependency ):
        self.node_connection_widgets.append(target_dependency_manager)

    def update_node_list(self):
        # Add nodes on the dependencies
        for target_dependency_manager in self.node_connection_widgets:
            for managed_nodes in self.managed_nodes.values():
                target_dependency_manager.add_node(managed_nodes.node)

        # Remove nods that do not exist anymore
        for target_dependency_manager in self.node_connection_widgets:
            for node in target_dependency_manager.nodes:
                # Check if node exists in managed nodes
                if node not in self.managed_nodes.values():
                    target_dependency_manager.remove_node(node)

    @property
    def active_nodes(self) -> List[GenericNode | AsyncGenericNode]:
        return [
            managed_node.node
            for managed_node in self.managed_nodes.values()
            if managed_node.node.state == managed_node.node.State.ACTIVE
        ]

    @property
    def selected_device(self) -> NodeTreeItem | None:
        """Get the selected device from the connected devices viewer"""
        selected_connected_items = self.loaded_devices_viewer.selectedItems()

        if selected_connected_items:
            assert len(selected_connected_items) == 1
            assert isinstance(selected_connected_items[0], NodeTreeItem)
            return selected_connected_items[0]

        return None

    def add_node(
        self,
        node: GenericNode | AsyncGenericNode,
        auto_init: bool = False,
        kwargs: Dict | None = None,
    ):
        assert node.name not in self.managed_nodes, f"Node with name {node.name} already exists"

        if kwargs is None:
            kwargs = {}

        self.managed_nodes[node.name] = ManagedNode(node=node, kwargs=kwargs)
        self.update_data()

        if auto_init:
            self.init_node(self.managed_nodes[node.name])

    def init_node(self, managed_node: ManagedNode):
        if isinstance(managed_node.node, AsyncGenericNode):
            asyncio.create_task(managed_node.node.attempt_init(**managed_node.kwargs))
        else:
            managed_node.node.attempt_init(**managed_node.kwargs)

    def update_data(self):
        # Add new devices
        for node in self.managed_nodes.values():
            if node not in self.node_treeitems:
                item = NodeTreeItem(node)
                self.loaded_devices_viewer.addTopLevelItem(item)
                self.node_treeitems[node] = item

        # Remove old devices
        for node in list(self.node_treeitems.keys()):
            if node not in self.managed_nodes.values():
                item = self.node_treeitems.pop(node)
                index = self.loaded_devices_viewer.indexOfTopLevelItem(item)
                self.loaded_devices_viewer.takeTopLevelItem(index)

        self.update_node_list()
        self.update_ui()

    def handle_remove(self):
        selected_device = self.selected_device

        if selected_device is None:
            return
        self.managed_nodes.pop(selected_device.managed_node.node.name)

        self.update_data()

    async def handle_init(self):
        selected_device = self.selected_device
        if selected_device is None:
            return

        node = selected_device.managed_node
        self.init_node(node)

        self.update_ui()

    async def handle_deinit(self):
        selected_device = self.selected_device
        if selected_device is None:
            return

        managed_node = selected_device.managed_node
        if isinstance(managed_node.node, AsyncGenericNode):
            await managed_node.node.attempt_deinit()
        else:
            managed_node.node.attempt_deinit()

        self.update_ui()

    def update_enabled_state(self):
        selected_device = self.selected_device
        self.init_btn.setEnabled(
            selected_device is not None
            and selected_device.managed_node.node.state
            not in [
                selected_device.managed_node.node.State.ACTIVE,
                selected_device.managed_node.node.State.INITIALIZING,
            ]
        )
        self.deinit_btn.setEnabled(
            selected_device is not None
            and selected_device.managed_node.node.state
            not in [
                selected_device.managed_node.node.State.STOPPED,
                selected_device.managed_node.node.State.IDLE,
            ]
        )

        self.remove_btn.setEnabled(selected_device is not None and not selected_device.managed_node.node.is_active())

    def update_ui(self):
        self.loaded_devices_viewer.refresh_ui()
        self.update_enabled_state()
