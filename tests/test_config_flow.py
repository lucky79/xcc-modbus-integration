"""Check that Home Assistant can send the xCC form to its frontend."""

import json
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, patch

from homeassistant.helpers.data_entry_flow import FlowManagerIndexView

from custom_components.xcc_modbus.config_flow import XccConfigFlow
from custom_components.xcc_modbus.const import DOMAIN


class ConfigFlowTest(IsolatedAsyncioTestCase):
    def setUp(self):
        self.flow = XccConfigFlow()
        self.flow.flow_id = "test-flow"
        self.flow.handler = DOMAIN
        self.view = FlowManagerIndexView(Mock())

    async def test_form_is_json_serializable(self):
        result = await self.flow.async_step_user()
        form = self.view._prepare_result_json(result)
        json.dumps(form)
        fields = {field["name"]: field for field in form["data_schema"]}
        self.assertEqual(fields["host"]["type"], "string")
        self.assertEqual(fields["port"]["default"], 502)

    async def test_invalid_host_renders_form_without_connecting(self):
        with patch("custom_components.xcc_modbus.config_flow.XccClient") as client:
            result = await self.flow.async_step_user({"host": "http://xcc.local"})
        client.assert_not_called()
        form = self.view._prepare_result_json(result)
        self.assertEqual(form["errors"], {"host": "invalid_host"})
        fields = {field["name"]: field for field in form["data_schema"]}
        self.assertEqual(fields["host"]["default"], "http://xcc.local")
