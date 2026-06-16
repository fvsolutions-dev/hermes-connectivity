import asyncio
import logging
import re

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from pydantic import BaseModel, Field


class BleDiscovery:
    """Filters BLE advertisements until a device matches all configured criteria.

    A device passes only if every configured filter matches. With no filters set,
    the first advertisement seen wins.
    """

    class Config(BaseModel):
        address: str | None = Field(
            description="Match against the device address",
            default=None,
        )
        name_match: str | None = Field(
            description="Regex matched against the advertised local name",
            default=None,
        )
        service_uuid: list[str] = Field(
            description="UUIDs of advertised services the device must broadcast (any-of match)",
            default_factory=list,
        )
        scan_timeout: float = Field(description="Timeout for scanning, in seconds", default=10)

    def __init__(self, config: Config, log: logging.Logger | None = None):
        self.config = config
        self.log = log or logging.getLogger(__name__)

        self._target_address = config.address.lower() if config.address is not None else None
        self._name_pattern = re.compile(config.name_match) if config.name_match is not None else None
        self._target_services = [uuid.lower() for uuid in config.service_uuid]

    def matches(self, device: BLEDevice, ad: AdvertisementData) -> bool:
        if self._target_address is not None and device.address.lower() != self._target_address:
            return False
        if self._name_pattern is not None and (
            ad.local_name is None or self._name_pattern.search(ad.local_name) is None
        ):
            return False
        if self._target_services and not any(
            uuid.lower() in self._target_services for uuid in ad.service_uuids
        ):
            return False
        return True

    async def scan(self) -> tuple[BLEDevice, BleakScanner]:
        """Scan until a matching device appears.

        Returns the device and the still-running scanner. The caller owns the
        scanner and is responsible for stopping it (typically after connecting,
        to avoid BlueZ dropping the device from its registry mid-connect).
        """
        found: asyncio.Future[BLEDevice] = asyncio.get_running_loop().create_future()

        def on_detection(device: BLEDevice, ad: AdvertisementData) -> None:
            if not found.done() and self.matches(device, ad):
                found.set_result(device)

        self.log.info(
            f"Scanning for device (address={self.config.address}, "
            f"name_match={self.config.name_match}, service_uuid={self.config.service_uuid})"
        )
        scanner = BleakScanner(
            detection_callback=on_detection,
            service_uuids=self._target_services or None,
        )
        await scanner.start()
        try:
            device = await asyncio.wait_for(found, timeout=self.config.scan_timeout)
        except asyncio.TimeoutError:
            await scanner.stop()
            raise TimeoutError("No device matched the configured filters") from None
        return device, scanner
