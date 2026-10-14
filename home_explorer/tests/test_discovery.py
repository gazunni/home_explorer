"""Safe offline tests. Never connect to a real Home Assistant instance."""
import sys
import types
import unittest

fake_websockets = types.ModuleType("websockets")
fake_sync = types.ModuleType("websockets.sync")
fake_client = types.ModuleType("websockets.sync.client")
fake_client.connect = lambda *args, **kwargs: None
sys.modules.setdefault("websockets", fake_websockets)
sys.modules.setdefault("websockets.sync", fake_sync)
sys.modules.setdefault("websockets.sync.client", fake_client)
from server import scan


class InventoryTests(unittest.TestCase):
    def test_normal_device(self):
        devices = [{"id": "1", "name": "Living Room Fan", "manufacturer": "Example",
                    "model": "F123"}]
        entities = [
            {"device_id": "1", "entity_id": "fan.living", "disabled_by": None},
            {"device_id": "1", "entity_id": "sensor.living_power", "disabled_by": None},
            {"device_id": "1", "entity_id": "switch.living", "disabled_by": "user"},
        ]
        data = scan(devices, entities)
        self.assertEqual(data["displayed_devices"], 1)
        self.assertEqual(data["devices"][0]["entity_count"], 2)

    def test_private_device_filtered(self):
        devices = [{"id": "private", "name": "Front Door Lock",
                    "manufacturer": "Example", "model": "L1"}]
        entities = [{"device_id": "private", "entity_id": "sensor.battery"}]
        result = scan(devices, entities)
        self.assertEqual(result["displayed_devices"], 0)
        self.assertEqual(result["hidden_private_devices"], 1)

    def test_sensitive_only_device(self):
        devices = [{"id": "lock", "name": "Generic", "manufacturer": "Example",
                    "model": "Unit"}]
        entities = [{"device_id": "lock", "entity_id": "lock.front_door"}]
        self.assertEqual(scan(devices, entities)["displayed_devices"], 0)

    def test_no_entity_identifiers_exposed(self):
        result = scan(
            [{"id": "p1", "name": "Fan", "manufacturer": "Example", "model": "Unit"}],
            [{"device_id": "p1", "entity_id": "fan.private_test_identifier"}],
        )
        self.assertNotIn("private_test_identifier", str(result))

    def test_limits(self):
        with self.assertRaises(RuntimeError):
            scan([{"id": str(i)} for i in range(1001)], [])


if __name__ == "__main__":
    unittest.main()
