"""Serialize access to the controller's only Modbus TCP connection."""

import asyncio
from collections.abc import Iterable

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import DEVICE_ID, TIMEOUT
from .registers import Register

ILLEGAL_DATA_ADDRESS = 2
DISCONNECT_GRACE = 0.25
MAX_BLOCK_WORDS = 64


class XccError(Exception):
    """An xCC request did not complete successfully."""


def contiguous_blocks(registers: Iterable[Register]):
    """Group adjacent addresses of the same register type."""
    block = []
    end = 0
    for register in sorted(registers, key=lambda r: (r.coil, r.address)):
        next_end = register.address + register.words
        if block and (
            block[0].coil != register.coil
            or end != register.address
            or next_end - block[0].address > MAX_BLOCK_WORDS
        ):
            yield tuple(block)
            block = []
        block.append(register)
        end = next_end
    if block:
        yield tuple(block)


class XccClient:
    """Keep reads and writes on one persistent, sequential connection."""

    def __init__(self, host: str, port: int, *, low_word_first: bool = False) -> None:
        self._client = AsyncModbusTcpClient(
            host,
            port=port,
            timeout=TIMEOUT,
            retries=0,
            reconnect_delay=0,
        )
        self._lock = asyncio.Lock()
        self._low_word_first = low_word_first
        self._unsupported: set[tuple[bool, int]] = set()

    async def close(self) -> None:
        """Close the socket after the current request finishes."""
        async with self._lock:
            was_connected = self._client.connected
            self._client.close()
            if was_connected:
                # The controller must release its only slot before setup opens another socket.
                await asyncio.sleep(DISCONNECT_GRACE)

    async def _connect(self) -> None:
        if not self._client.connected:
            self._unsupported.clear()
            if not await self._client.connect():
                raise XccError("Nelze navázat spojení s xCC")

    async def read(
        self, blocks: Iterable[tuple[Register, ...]]
    ) -> dict[str, bool | int | float]:
        """Read entity values, tolerating unavailable optional registers."""
        values = {}
        async with self._lock:
            try:
                await self._connect()
                if self._unsupported:
                    blocks = contiguous_blocks(
                        register
                        for block in blocks
                        for register in block
                        if (register.coil, register.address) not in self._unsupported
                    )
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
        count = sum(register.words for register in block)
        response = await read(first.address, count=count, device_id=DEVICE_ID)
        if response.isError():
            if getattr(response, "exception_code", None) == ILLEGAL_DATA_ADDRESS:
                if len(block) > 1:
                    middle = len(block) // 2
                    await self._read_block(block[:middle], values)
                    await self._read_block(block[middle:], values)
                else:
                    self._unsupported.add((first.coil, first.address))
                return
            raise XccError(str(response))
        raw_values = response.bits if first.coil else response.registers
        if len(raw_values) < count:
            raise XccError(f"Neúplná odpověď pro adresu {first.address}")
        offset = 0
        for register in block:
            end = offset + register.words
            values[register.key] = register.decode(
                *raw_values[offset:end],
                low_word_first=self._low_word_first,
            )
            offset = end

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
