"""Serialize access to the controller's only Modbus TCP connection."""

import asyncio
from collections.abc import Iterable
from itertools import groupby

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import DEVICE_ID, TIMEOUT
from .registers import Register

ILLEGAL_DATA_ADDRESS = 2
DISCONNECT_GRACE = 0.25


class XccError(Exception):
    """An xCC request did not complete successfully."""


def contiguous_blocks(registers: Iterable[Register]):
    """Group adjacent addresses of the same register type."""
    for _, same_type in groupby(
        sorted(registers, key=lambda r: (r.coil, r.address)), key=lambda r: r.coil
    ):
        for _, adjacent in groupby(
            enumerate(same_type), key=lambda item: item[1].address - item[0]
        ):
            yield tuple(register for _, register in adjacent)


class XccClient:
    """Keep reads and writes on one persistent, sequential connection."""

    def __init__(self, host: str, port: int) -> None:
        self._client = AsyncModbusTcpClient(
            host,
            port=port,
            timeout=TIMEOUT,
            retries=0,
            reconnect_delay=0,
        )
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        """Close the socket after the current request finishes."""
        async with self._lock:
            was_connected = self._client.connected
            self._client.close()
            if was_connected:
                # The controller must release its only slot before setup opens another socket.
                await asyncio.sleep(DISCONNECT_GRACE)

    async def _connect(self) -> None:
        if not self._client.connected and not await self._client.connect():
            raise XccError("Nelze navázat spojení s xCC")

    async def read(
        self, blocks: Iterable[tuple[Register, ...]]
    ) -> dict[str, bool | int | float]:
        """Read entity values, tolerating unavailable optional registers."""
        values = {}
        async with self._lock:
            try:
                await self._connect()
                for block in blocks:
                    await self._read_block(block, values)
            except (OSError, ModbusException, XccError) as err:
                self._client.close()
                raise XccError(str(err)) from err
        return values

    async def _read_block(self, block, values) -> None:
        first = block[0]
        read = (
            self._client.read_coils
            if first.coil
            else self._client.read_holding_registers
        )
        response = await read(first.address, count=len(block), device_id=DEVICE_ID)
        if response.isError():
            if getattr(response, "exception_code", None) == ILLEGAL_DATA_ADDRESS:
                if len(block) > 1:
                    middle = len(block) // 2
                    await self._read_block(block[:middle], values)
                    await self._read_block(block[middle:], values)
                return
            raise XccError(str(response))
        raw_values = response.bits if first.coil else response.registers
        if len(raw_values) < len(block):
            raise XccError(f"Neúplná odpověď pro adresu {first.address}")
        for register, raw in zip(block, raw_values):
            values[register.key] = register.decode(raw)

    async def write(self, register: Register, value: bool | float) -> None:
        """Write one documented RW coil or one holding register."""
        if not register.writable:
            raise XccError(f"Adresa {register.address} je jen pro čtení")
        async with self._lock:
            try:
                await self._connect()
                if register.coil:
                    response = await self._client.write_coil(
                        register.address,
                        bool(value),
                        device_id=DEVICE_ID,
                    )
                else:
                    response = await self._client.write_register(
                        register.address,
                        register.encode(value),
                        device_id=DEVICE_ID,
                    )
            except (OSError, ModbusException, XccError) as err:
                self._client.close()
                raise XccError(str(err)) from err
            if response.isError():
                raise XccError(str(response))
