import unittest
import json
from unittest.mock import patch
from server import scan, referenced_devices, automation_links, registry_request, device_diagnostics, power_dependency, load_power_dependencies, save_power_dependencies

class ScanTests(unittest.TestCase):
    def test_confirmed_outlet_off_is_not_appliance_failure(self):
        x = power_dependency('Sample Appliance',
                             {'switch.sample_outlet':'off'},
                             {'Sample Appliance':'switch.sample_outlet'})
        self.assertEqual(x['supply_state'],'off')
        self.assertNotIn('switch.sample_outlet',str(x))
        self.assertIn('may be unavailable',x['interpretation'])
    def test_confirmed_outlet_on_does_not_imply_operation(self):
        x = power_dependency('Sample Appliance',
                             {'switch.sample_outlet':'on'},
                             {'Sample Appliance':'switch.sample_outlet'})
        self.assertIn('does not prove',x['interpretation'])
    def test_no_inferred_wiring_for_other_devices(self):
        self.assertIsNone(power_dependency('Another Dehumidifier',
                          {'switch.sample_outlet':'off'},
                          {'Sample Appliance':'switch.sample_outlet'}))
    def test_loader_ignores_invalid_mapping_but_preserves_valid(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'mapping.json'
            path.write_text(json.dumps({'Appliance':'switch.good_outlet',
                                        'Private':'switch.secret_token'}))
            self.assertEqual(load_power_dependencies(path),
                             {'Appliance':'switch.good_outlet'})
    def test_mapping_survives_repeated_save(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'mapping.json'
            save_power_dependencies({'Appliance':'switch.outlet_one'}, path)
            save_power_dependencies({'Appliance':'switch.outlet_two'}, path)
            self.assertEqual(load_power_dependencies(path),
                             {'Appliance':'switch.outlet_two'})
    def test_replacing_a_saved_mapping(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'mapping.json'
            save_power_dependencies({'Appliance':'switch.outlet_one'}, path)
            save_power_dependencies({'Appliance':'switch.outlet_two'}, path)
            self.assertEqual(load_power_dependencies(path),
                             {'Appliance':'switch.outlet_two'})
    def test_save_creates_private_data_directory(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'nested' / 'mapping.json'
            save_power_dependencies({'Appliance':'switch.outlet'}, path)
            self.assertEqual(load_power_dependencies(path), {'Appliance':'switch.outlet'})
    def test_data_file_is_outside_source_tree(self):
        from pathlib import Path
        from server import DEPENDENCY_FILE
        self.assertEqual(DEPENDENCY_FILE, Path('/data/power_dependencies.json'))
    def test_save_reload_local_mapping(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'mapping.json'
            save_power_dependencies({'Appliance':'switch.power_outlet'},path)
            self.assertEqual(load_power_dependencies(path),{'Appliance':'switch.power_outlet'})
    def test_reject_private_mapping(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                save_power_dependencies({'Appliance':'switch.secret_token'},Path(folder)/'m.json')
    def test_dependency_config_rejects_sensitive_entities(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'dependencies.json'
            path.write_text('{"Fan":"switch.fan_outlet","Private":"switch.secret_token"}')
            self.assertEqual(load_power_dependencies(path), {'Fan':'switch.fan_outlet'})
    def test_mixed_sensor_availability_is_not_device_failure(self):
        data = [{'state':'on'},{'state':'unavailable'},{'state':'unknown'}]
        self.assertEqual(device_diagnostics(data), {
            'status':'Partially available','available':1,'unavailable':1,'unknown':1})
    def test_all_unavailable_not_assumed_scheduled_off(self):
        self.assertEqual(device_diagnostics([{'state':'unavailable'}])['status'],
                         'Readings unavailable')
    def one(self, domain):
        return scan([{'id':'d1','name':'Living Room Device','manufacturer':'Example','model':'M1'}],
                    [{'device_id':'d1','entity_id':domain+'.test'}])['devices'][0]
    def test_read_only_automation_websocket_schema(self):
        class FakeWS:
            def __init__(self):
                self.commands = []
                self.replies = iter([
                    {'type':'auth_required'}, {'type':'auth_ok'},
                    {'id':1,'success':True,'result':[]},
                    {'id':2,'success':True,'result':[]},
                    {'id':3,'success':True,'result':[{'entity_id':'automation.test_1','state':'on'}]},
                    {'id':4,'success':True,'result':{}},
                    {'id':5,'success':True,'result':{'config':{
                        'actions':[{'target':{'entity_id':'switch.fan'}}]}}}
                ])
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def send(self, value):
                self.commands.append(json.loads(value))
            def recv(self, **kwargs):
                return json.dumps(next(self.replies))
        fake = FakeWS()
        with patch.dict('os.environ',{'SUPERVISOR_TOKEN':'dummy'}):
            with patch('server.connect',return_value=fake):
                result = registry_request()
        self.assertEqual(len(result), 6)
        self.assertEqual(result[4][0]['actions'][0]['target']['entity_id'],'switch.fan')
        self.assertEqual(fake.commands[-1],{'id':5,'type':'automation/config',
                                            'entity_id':'automation.test_1'})
        self.assertTrue(all(cmd.get('type') not in ('call_service','automation/trigger')
                            for cmd in fake.commands))
    def test_structured_automation_relations(self):
        config={'triggers':[{'trigger':'state','entity_id':'sensor.fan_temperature'}],
                'conditions':[{'condition':'state','entity_id':'switch.fan'}],
                'actions':[{'action':'switch.turn_on','target':{'entity_id':'switch.fan'}}]}
        mapping={'sensor.fan_temperature':'dev1','switch.fan':'dev1'}
        self.assertEqual(referenced_devices(config,mapping),
                         {('dev1','trigger'),('dev1','condition'),('dev1','action')})
        links=automation_links([config],mapping)
        self.assertEqual(links['dev1'],{'trigger':1,'condition':1,'action':1})
    def test_templates_and_arbitrary_text_not_matched(self):
        config={'triggers':[{'value_template':'sensor.fan_temperature'}],
                'actions':[{'data':{'message':'switch.fan'}},
                           {'target':{'entity_id':'{{ states.sensor.secret }}'}}]}
        self.assertEqual(referenced_devices(config,{'sensor.fan_temperature':'x','switch.fan':'x'}),set())
    def test_related_counts_only_no_private_config_leak(self):
        config={'alias':'secret family alarm',
                'triggers':[{'entity_id':'sensor.temp'}],
                'actions':[{'target':{'device_id':'d1'}}]}
        result=scan([{'id':'d1','name':'Fan'}],
                    [{'device_id':'d1','entity_id':'sensor.temp'}],configurations=[config],attempted=1)
        self.assertEqual(result['devices'][0]['automation_links']['action'],1)
        self.assertEqual(result['automations']['configurations_checked'],1)
        self.assertNotIn('secret family alarm',str(result))
        self.assertNotIn('d1',str(result))
    def test_sensitive_entity_not_linked_to_automation(self):
        config={'actions':[{'target':{'entity_id':'switch.secret_device'}}]}
        result=scan([{'id':'d1','name':'Fan'}],
                    [{'device_id':'d1','entity_id':'switch.secret_device'},
                     {'device_id':'d1','entity_id':'sensor.fan_temperature'}],
                    configurations=[config],attempted=1)
        self.assertEqual(result['devices'][0]['automation_links']['action'],0)
    def test_missing_configurations_not_falsely_reported_complete(self):
        result=scan([],[],configurations=[],attempted=15)
        self.assertEqual(result['automations']['configurations_checked'],0)
        self.assertEqual(result['automations']['lookup_attempted'],15)
    def test_service_catalog_is_domain_wide_only(self):
        x = scan([{'id':'d1','name':'Lamp'}],
                 [{'device_id':'d1','entity_id':'light.desk'}],
                 [{'entity_id':'light.desk','state':'on','attributes':{'supported_features':5}}],
                 {'light':{'turn_on':{},'turn_off':{}}})['devices'][0]
        self.assertEqual(x['capabilities'][0]['domain_services'],['turn_off','turn_on'])
        self.assertEqual(x['capabilities'][0]['members'][0]['supported_features'],5)
    def test_automations_redacted_to_counts(self):
        x=scan([],[],[{'entity_id':'automation.private_family_name','state':'on'},
                        {'entity_id':'automation.another','state':'off'}])
        self.assertEqual(x['automations']['enabled'],1)
        self.assertNotIn('private_family_name',str(x))
    def test_private_options_filtered(self):
        x=scan([{'id':'d1','name':'Fan'}],
               [{'device_id':'d1','entity_id':'select.fan_mode'}],
               [{'entity_id':'select.fan_mode','state':'auto','attributes':{'options':['Auto','secret PIN','Eco']}}])
        self.assertEqual(x['devices'][0]['capabilities'][0]['members'][0]['options'],['Auto','Eco'])
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
    def test_summary_uses_actual_registered_states(self):
        result = scan([{'id':'d1','name':'Dryer'}],
                      [{'device_id':'d1','entity_id':'sensor.dryer_current_status'},
                       {'device_id':'d1','entity_id':'sensor.dryer_remaining_time'}],
                      [{'entity_id':'sensor.dryer_current_status','state':'power_off'},
                       {'entity_id':'sensor.dryer_remaining_time','state':'unknown'}])
        self.assertEqual(result['devices'][0]['summary'], [
            {'label':'Current status','state':'power_off','domain':'sensor'}])
    def test_summary_excludes_private_and_absent_readings(self):
        result = scan([{'id':'d1','name':'Lamp'}],
                      [{'device_id':'d1','entity_id':'sensor.lamp_battery'},
                       {'device_id':'d1','entity_id':'sensor.secret_battery'}],
                      [{'entity_id':'sensor.lamp_battery','state':'unknown'},
                       {'entity_id':'sensor.secret_battery','state':'70'}])
        self.assertEqual(result['devices'][0]['summary'], [])
    def test_members_include_entity_domain_and_state(self):
        item = scan([{'id':'d1','name':'Dryer'}],
                    [{'device_id':'d1','entity_id':'sensor.dryer_current_status'}],
                    [{'entity_id':'sensor.dryer_current_status','state':'power_off'}])['devices'][0]
        member = item['capabilities'][0]['members'][0]
        self.assertEqual(member['domain'], 'sensor')
        self.assertEqual(member['state'], 'power_off')
    def test_state_does_not_override_private_entity_redaction(self):
        result = scan([{'id':'d1','name':'Lamp'}],
                      [{'device_id':'d1','entity_id':'light.secret_identifier'}],
                      [{'entity_id':'light.secret_identifier','state':'on'}])
        self.assertEqual(result['displayed_devices'], 0)
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
