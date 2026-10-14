import unittest
from server import scan

class ScanTests(unittest.TestCase):
    def one(self, domain):
        return scan([{'id':'d1','name':'Living Room Device','manufacturer':'Example','model':'M1'}],
                    [{'device_id':'d1','entity_id':domain+'.test'}])['devices'][0]
    def test_measurements_not_control(self):
        x=self.one('sensor')
        self.assertEqual(x['observable_categories'],1)
        self.assertEqual(x['potential_control_categories'],0)
        self.assertEqual(x['capabilities'][0]['access'],'Information only')
    def test_binary_sensor_information(self):
        self.assertEqual(self.one('binary_sensor')['capabilities'][0]['access'],'Information only')
    def test_switch_possible_not_confirmed(self):
        x=self.one('switch')
        self.assertEqual(x['potential_control_categories'],1)
        self.assertIn('not been checked',x['capabilities'][0]['verification'])
    def test_no_vendor_only_conclusion(self):
        x=self.one('light')
        self.assertNotIn('requires app',str(x))
        self.assertIn('cannot be determined',scan([],[])['note'])
    def test_no_raw_ids(self):
        x=scan([{'id':'abcPRIVATE','name':'Lamp'}],
               [{'device_id':'abcPRIVATE','entity_id':'light.secret_identifier'}])
        self.assertNotIn('abcPRIVATE',str(x))
        self.assertNotIn('secret_identifier',str(x))
    def test_sensitive_name(self):
        x=scan([{'id':'1','name':'Front Door Lock'}],
               [{'device_id':'1','entity_id':'sensor.battery'}])
        self.assertEqual(x['displayed_devices'],0)
    def test_parent(self):
        x=scan([{'id':'p','name':'Vacuum'},{'id':'c','name':'Dock','via_device_id':'p'}],
               [{'device_id':'p','entity_id':'vacuum.main'},{'device_id':'c','entity_id':'sensor.dock'}])
        self.assertEqual(next(d for d in x['devices'] if d['name']=='Dock')['related_to'],'Vacuum')
    def test_sense_virtual(self):
        x=scan([{'id':'1','name':'Bear','manufacturer':'Sense Labs, Inc.','model':'Sense'}],
               [{'device_id':'1','entity_id':'sensor.power'}])
        self.assertTrue(x['devices'][0]['virtual'])
    def test_size_limit(self):
        with self.assertRaises(RuntimeError):
            scan([{'id':str(i)} for i in range(1001)],[])
    def test_disabled_entity(self):
        x=scan([{'id':'1','name':'Fan'}],
               [{'device_id':'1','entity_id':'fan.one','disabled_by':'user'}])
        self.assertEqual(x['displayed_devices'],0)

if __name__ == '__main__':
    unittest.main()
