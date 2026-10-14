import unittest
from server import scan
class ScanTest(unittest.TestCase):
    def test_normal(self):
        result=scan([{'id':'1','name':'Living Fan','manufacturer':'Example','model':'F1'}],[{'device_id':'1','entity_id':'fan.living'},{'device_id':'1','entity_id':'sensor.power'}])
        self.assertEqual(result['displayed_devices'],1)
        self.assertEqual(result['devices'][0]['entity_count'],2)
    def test_private(self):
        result=scan([{'id':'1','name':'Front Door Lock'}],[{'device_id':'1','entity_id':'sensor.battery'}])
        self.assertEqual(result['displayed_devices'],0)
    def test_no_ids(self):
        result=scan([{'id':'1','name':'Fan'}],[{'device_id':'1','entity_id':'fan.private_identifier'}])
        self.assertNotIn('private_identifier',str(result))
    def test_limits(self):
        with self.assertRaises(RuntimeError):scan([{'id':str(i)} for i in range(1001)],[])


class DiscoveryV030Tests(unittest.TestCase):
    def test_parent_grouping_without_registry_id_leak(self):
        devices=[{'id':'p1','name':'Vacuum','manufacturer':'Roborock','model':'S5V'},
                 {'id':'c1','name':'Dock','manufacturer':'Roborock','model':'Dock','via_device_id':'p1'}]
        entities=[{'device_id':'p1','entity_id':'vacuum.example'},{'device_id':'c1','entity_id':'sensor.dock'}]
        result=scan(devices,entities)
        dock=next(x for x in result['devices'] if x['name']=='Dock')
        self.assertEqual(dock['related_to'],'Vacuum')
        self.assertNotIn('p1',str(result))
        self.assertNotIn('via_device_id',str(result))

    def test_sense_is_virtual_not_merged(self):
        devices=[{'id':'s1','name':'Bear','manufacturer':'Sense Labs, Inc.','model':'Sense'},
                 {'id':'s2','name':'Bear','manufacturer':'Sense Labs, Inc.','model':'Sense'}]
        entities=[{'device_id':'s1','entity_id':'sensor.bear_1'},
                  {'device_id':'s2','entity_id':'sensor.bear_2'}]
        result=scan(devices,entities)
        self.assertEqual(result['displayed_devices'],2)
        self.assertEqual(result['virtual_monitor_entries'],2)
        self.assertTrue(all(x['virtual'] for x in result['devices']))

    def test_ideas_are_not_claimed_automations(self):
        result=scan([{'id':'x','name':'Room fan','manufacturer':'Example'}],
                    [{'device_id':'x','entity_id':'fan.room'}])
        self.assertTrue(result['devices'][0]['ideas'])
        self.assertIn('not been verified',result['note'])

    def test_private_name(self):
        result=scan([{'id':'x','name':'Cindy Button','manufacturer':'Sample'}],
                    [{'device_id':'x','entity_id':'sensor.battery'}])
        self.assertEqual(result['displayed_devices'],0)
