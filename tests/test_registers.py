"""Coverage and decoding checks for the vendor's protocol 2.5 map."""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock, patch

from custom_components.xcc_modbus.const import FEATURES
from custom_components.xcc_modbus.modbus import XccClient, contiguous_blocks
from custom_components.xcc_modbus.registers import (
    METER_ENERGY,
    METER_POWER,
    Section,
    registers_for,
)
from custom_components.xcc_modbus.sensor import XccTotalPowerSensor

ALL_EQUIPMENT = {
    "heating_circuits": 12,
    "dhw_tanks": 2,
    "zones": 16,
    "external_inputs": 16,
    "outdoor_units": 10,
    "pools": 2,
    "mbus_meters": 4,
    "features": FEATURES,
}


class RegisterMapTest(TestCase):
    def test_complete_map_without_reserved_or_duplicate_addresses(self):
        registers = registers_for(ALL_EQUIPMENT)
        self.assertEqual(len(registers), len({register.key for register in registers}))
        for coil, expected in (
            (False, set(range(452)) - {295, 296, 297}),
            (True, set(range(126)) - {69}),
        ):
            addresses = [
                register.address + offset
                for register in registers
                if register.coil == coil
                for offset in range(register.words)
            ]
            self.assertEqual(len(addresses), len(expected))
            self.assertEqual(set(addresses), expected)

    def test_power_requires_all_phases_and_uses_kw(self):
        data = {"meter_power_l1": 812.3, "meter_power_l2": 551, "meter_power_l3": 136.7}
        coordinator = SimpleNamespace(
            data=data,
            last_update_success=True,
            devices={Section.SYSTEM: {}, Section.METER: {}},
        )
        entry = SimpleNamespace(runtime_data=coordinator, entry_id="entry")
        sensor = XccTotalPowerSensor(entry)
        self.assertEqual(sensor.native_unit_of_measurement, "kW")
        self.assertEqual(sensor.native_value, 1.5)
        self.assertTrue(sensor.available)
        data.pop("meter_power_l3")
        self.assertIsNone(sensor.native_value)
        self.assertFalse(sensor.available)


class ModbusReadTest(IsolatedAsyncioTestCase):
    async def test_mixed_word_widths_and_low_word_first(self):
        read = AsyncMock(
            return_value=Mock(
                isError=Mock(return_value=False),
                registers=[24, 1, 8123, 5510, 1367],
            )
        )
        client = Mock(connected=True, read_holding_registers=read)
        with patch(
            "custom_components.xcc_modbus.modbus.AsyncModbusTcpClient",
            return_value=client,
        ):
            xcc = XccClient("xcc.local", 502, low_word_first=True)
        blocks = tuple(contiguous_blocks((*METER_ENERGY[-1:], *METER_POWER)))
        values = await xcc.read(blocks)
        read.assert_awaited_once_with(355, count=5, device_id=1)
        self.assertEqual(values["meter_energy_total"], 6556.0)
        self.assertEqual(values["meter_power_l1"], 812.3)
        self.assertEqual(values["meter_power_l3"], 136.7)

    async def test_illegal_address_splits_without_splitting_a_double_word(self):
        async def read(address, *, count, device_id):
            if address <= 356 < address + count:
                return Mock(isError=Mock(return_value=True), exception_code=2)
            return Mock(isError=Mock(return_value=False), registers=[1000] * count)

        client = Mock(
            connected=True, read_holding_registers=AsyncMock(side_effect=read)
        )
        with patch(
            "custom_components.xcc_modbus.modbus.AsyncModbusTcpClient",
            return_value=client,
        ):
            xcc = XccClient("xcc.local", 502)
        blocks = tuple(contiguous_blocks((*METER_ENERGY[-1:], *METER_POWER)))
        self.assertNotIn("meter_energy_total", await xcc.read(blocks))
        client.read_holding_registers.reset_mock()
        self.assertEqual((await xcc.read(blocks))["meter_power_l3"], 100)
        client.read_holding_registers.assert_awaited_once_with(
            357, count=3, device_id=1
        )
