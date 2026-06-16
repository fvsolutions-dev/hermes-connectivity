import asyncio
from typing import Awaitable, Callable, Literal

from bleak import BleakClient
from pydantic import Field

from node_hermes_core.generic_node.generic import AsyncGenericNode

from .discovery import BleDiscovery

# Connection-listener callbacks: invoked with the live client on (re)connect,
# and with no args on disconnect. Used by BleCharacteristicNode to (re)subscribe.
ConnectCallback = Callable[[BleakClient], Awaitable[None]]
DisconnectCallback = Callable[[], Awaitable[None]]


class BleNode(AsyncGenericNode):
    """Owns the BLE link, NON-BLOCKING. `init()` returns immediately (the node
    goes ACTIVE = "manager running") and a background task scans → connects →
    monitors → reconnects. This keeps the UI responsive and reflecting live
    state (scanning/connecting/connected/disconnected) instead of freezing in
    INITIALIZING for the whole blocking scan+connect and hard-erroring on a
    timeout. Dependents subscribe via add_connection_listener() rather than
    requiring a live connection at their own init."""

    class Config(AsyncGenericNode.Config, BleDiscovery.Config):
        type: Literal["ble_node"] = "ble_node"
        connection_timeout: float = Field(description="The timeout for connection", default=5)
        reconnect_interval: float = Field(
            description="Seconds to wait before retrying after a failed/lost connection",
            default=2.0,
        )

    config: Config
    client: BleakClient | None = None
    # Live, human-readable link state for the UI: scanning|connecting|connected|disconnected
    connection_status: str = "idle"

    async def init(self):
        self._stop = False
        self._listeners: list[tuple[ConnectCallback, DisconnectCallback]] = []
        self._disconnected_evt: asyncio.Event | None = None
        self.client = None
        self.connection_status = "scanning"
        # Background manager — the node is ACTIVE the moment this is spawned.
        self._conn_task = asyncio.create_task(self._connection_loop())

    async def deinit(self):
        self._stop = True
        task = getattr(self, "_conn_task", None)
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
            self._conn_task = None
        if self.client is not None:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.client = None
        self.connection_status = "idle"

    def add_connection_listener(self, on_connect: ConnectCallback, on_disconnect: DisconnectCallback):
        """Register (re)subscribe / teardown callbacks tied to the link lifecycle.
        If already connected, fire on_connect now so a late-registering dependent
        still subscribes."""
        self._listeners.append((on_connect, on_disconnect))
        if self.client is not None and self.client.is_connected:
            asyncio.create_task(self._safe(on_connect(self.client), "on_connect"))

    @property
    def is_connected(self) -> bool:
        return self.client is not None and self.client.is_connected

    async def _safe(self, coro: Awaitable[None], what: str):
        try:
            await coro
        except Exception:
            self.log.exception(f"BLE {what} listener failed")

    async def _connection_loop(self):
        """Scan → connect → notify listeners → wait for disconnect → retry.
        Never raises out of the node: failures just trigger a backoff + retry,
        so the node stays ACTIVE and the UI keeps reflecting live status."""
        while not self._stop:
            scanner = None
            try:
                self.connection_status = "scanning"
                discovery = BleDiscovery(self.config, log=self.log)
                device, scanner = await discovery.scan()

                self.connection_status = "connecting"
                self.log.info(f"Connecting to BLE device {device}")
                self._disconnected_evt = asyncio.Event()
                client = BleakClient(device, disconnected_callback=self._on_disconnected)
                await asyncio.wait_for(client.connect(), timeout=self.config.connection_timeout)
                await scanner.stop()
                scanner = None

                self.client = client
                self.connection_status = "connected"
                self.log.info("Connected to BLE device")
                for on_connect, _ in list(self._listeners):
                    await self._safe(on_connect(client), "on_connect")

                # Block here until the link drops (disconnected_callback fires).
                await self._disconnected_evt.wait()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log.warning(f"BLE connection attempt failed: {e}")
            finally:
                if scanner is not None:
                    try:
                        await scanner.stop()
                    except Exception:
                        pass

            # Link is down (drop or failed attempt) — tear down + notify, then retry.
            self.client = None
            for _, on_disconnect in list(self._listeners):
                await self._safe(on_disconnect(), "on_disconnect")
            if not self._stop:
                self.connection_status = "disconnected"
                await asyncio.sleep(self.config.reconnect_interval)

    def _on_disconnected(self, client: BleakClient):
        self.log.info("Disconnected from BLE device")
        self.connection_status = "disconnected"
        if self._disconnected_evt is not None:
            self._disconnected_evt.set()

    def dump_characteristics(self):
        if self.client is None:
            self.log.warning("Not connected to any BLE device")
            return
        for service in self.client.services:  # type: ignore
            print(f"Service: {service.uuid}")
            for char in service.characteristics:
                print(f"  Characteristic: {char.uuid}, properties: {char.properties}")

    def __str__(self):
        return f"{self.config.name}"

    @property
    def widget(self):
        from .qt.widget import BleWidget

        return BleWidget
