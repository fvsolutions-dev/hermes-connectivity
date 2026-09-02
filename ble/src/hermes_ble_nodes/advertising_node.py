import re
import time
from typing import List, Literal

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from node_hermes_core.datatypes import BinaryDataPacket
from node_hermes_core.generic_node.generic import AsyncGenericNode
from node_hermes_core.source_sink_node import SourceNode
from pydantic import Field
from dataclasses import dataclass

@dataclass
class AdvertisementDataPacket(BinaryDataPacket):
    device: str
    rssi: int
    name: str = ""

class BleAdvertisingNode(SourceNode, AsyncGenericNode):
    """Source node that scans for BLE advertisements and emits each one as a data packet.

    Also keeps a seen-device registry (refreshed on every advert) so connection
    nodes can resolve a live `BLEDevice` from the adverts already flowing,
    instead of starting a second discovery scan — see `BleNode`'s
    `device_provider`."""

    class Config(SourceNode.Config):
        type: Literal["ble_advertising_node"] = "ble_advertising_node"
        address: str | list[str] | None = Field(
            description="Optional MAC/UUID filter; only emit advertisements from these addresses (string or list of strings). If None, emit from all devices.",
            default=None,
        )
        name_match: str | None = Field(
            description="Optional regex matched against the advertised local name "
            "(falling back to the resolved device name), e.g. 'Sensor-.*'; only emit "
            "advertisements from matching devices. Note: frames that carry no name "
            "(a bare advert whose name arrives in the scan response) are dropped.",
            default=None,
        )
        service_uuids: List[str] | None = Field(
            description="Optional list of service UUIDs to filter on",
            default=None,
        )
        scanning_mode: Literal["active", "passive"] = Field(
            description="BLE scanning mode",
            default="active",
        )
        company_id: int|None = Field(
            description="Optional manufacturer ID to filter on (e.g. 0x004C for Apple)",
            default=None,
        )
        deduplicate: bool = Field(
            description="Whether to deduplicate advertisements (only emit data from each unique device address once)",
            default=False,
        )
        debug: bool = Field(
            description=(
                "Log every advertisement this node emits (device, rssi, company id, payload hex). "
                "Useful to confirm data is arriving at all, since the payload is a BinaryDataPacket "
                "that downstream print/tracker nodes cannot render."
            ),
            default=False,
        )
        duplicate_data: bool = Field(
            description=(
                "BlueZ only: set the DuplicateData discovery filter so every advertising frame is "
                "reported, instead of only BlueZ-visible property changes. Required to receive a "
                "broadcast data stream reliably — without it BlueZ can withhold a device whose "
                "adverts it considers unchanged, and that device then never produces any data. "
                "Pair with deduplicate=True to drop the resulting per-channel repeats."
            ),
            default=False,
        )

    config: Config
    scanner: BleakScanner | None = None

    def __init__(self, config: Config):
        super().__init__(config)
        self.last_data_per_uuid: dict[str, bytes] = {}
        self.seen_devices: dict[str, BLEDevice] = {}
        self._name_pattern = re.compile(config.name_match) if config.name_match else None

    def get_seen_device(self, address: str) -> BLEDevice | None:
        return self.seen_devices.get(address)

    async def init(self):
        self.log.info("Starting BLE advertisement scanner")
        backend_args = {}
        if self.config.duplicate_data:
            # Imported lazily: bleak.args.bluez only exists on bleak >= 3, and this
            # package supports older versions where the filter simply isn't available.
            from bleak.args.bluez import BlueZScannerArgs

            backend_args["bluez"] = BlueZScannerArgs(filters={"DuplicateData": True})

        self.scanner = BleakScanner(
            detection_callback=self._on_advertisement,
            service_uuids=self.config.service_uuids,
            scanning_mode=self.config.scanning_mode,
            **backend_args,
        )
        await self.scanner.start()

    async def deinit(self):
        if self.scanner is not None:
            await self.scanner.stop()
            self.scanner = None

    def _on_advertisement(self, device: BLEDevice, advertisement_data: AdvertisementData):
        # Registry entries stay fresh because they're refreshed on every advert
        # (before any filtering) — BlueZ needs a recently-seen device to connect.
        self.seen_devices[device.address] = device

        if self.config.address is not None:
            if isinstance(self.config.address, str):
                if device.address != self.config.address:
                    return
            elif isinstance(self.config.address, list):
                if device.address not in self.config.address:
                    return

        if self._name_pattern is not None:
            name = advertisement_data.local_name or device.name or ""
            if self._name_pattern.search(name) is None:
                return

        for company_id, payload in advertisement_data.manufacturer_data.items():
            if self.config.company_id is not None and company_id != self.config.company_id:
                continue
            
            if self.config.deduplicate:
                if device.address in self.last_data_per_uuid and self.last_data_per_uuid[device.address] == payload:
                    return  
                self.last_data_per_uuid[device.address] = payload
            
            if self.config.debug:
                self.log.info(
                    f"{device.address} {advertisement_data.rssi:4d} dBm "
                    f"mfr[{company_id:#06x}] {len(payload):3d} B {payload.hex()}"
                )

            packet = AdvertisementDataPacket(
                source=self.config.name,
                timestamp=time.time(),
                data=payload,
                device=device.address,
                rssi=advertisement_data.rssi,
                name=advertisement_data.local_name or device.name or "",
            )

            self.send_data(packet)
            
    def get_data(self) -> None:
        return None
