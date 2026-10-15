import unittest
import json
from unittest.mock import patch, Mock
from server import scan, referenced_devices, automation_links, registry_request, device_diagnostics, power_dependency, load_power_dependencies, save_power_dependencies, Handler, PRIVATE_NAME, read_query, SCAN_LOCK

class ScanTests(unittest.TestCase):
    def test_electrical_snapshot_single_switch_is_read_only(self):
        device = [{'id':'outlet','name':'Refrigerator','manufacturer':'TP-Link','model':'EP25'}]
        entities = [{'device_id':'outlet','entity_id':'switch.fridge_power'},
                    {'device_id':'outlet','entity_id':'sensor.fridge_current_consumption'}]
        states = [{'entity_id':'switch.fridge_power','state':'on','attributes':{}},
                  {'entity_id':'sensor.fridge_current_consumption','state':'136.9',
                   'last_updated':'2026-10-15T01:00:00+00:00',
                   'attributes':{'device_class':'power','unit_of_measurement':'W'}}]
        item = scan(device, entities, states)['devices'][0]
        self.assertEqual(item['electrical'][0]['value'],136.9)
        self.assertEqual(item['electrical'][0]['kind'],'power')
        self.assertEqual(item['electrical'][0]['unit'],'W')
        self.assertEqual(item['electrical'][0]['last_updated'],states[1]['last_updated'])
    def test_switch_transition_is_included_for_power_evidence(self):
        devices=[{'id':'plug','name':'Refrigerator','manufacturer':'TP-Link','model':'EP25'}]
        entities=[{'device_id':'plug','entity_id':'switch.refrigerator_2'}]
        states=[{'entity_id':'switch.refrigerator_2','state':'on',
                 'last_changed':'2026-10-15T13:37:00-04:00',
                 'last_updated':'2026-10-15T13:37:00-04:00',
                 'attributes':{'friendly_name':'Refrigerator'}}]
        result=scan(devices,entities,states)
        members=[m for cap in result['devices'][0]['capabilities'] for m in cap['members']]
        self.assertEqual(members[0]['last_changed'],'2026-10-15T13:37:00-04:00')
        self.assertEqual(members[0]['state'],'on')

    def test_ep25_outlet_and_led_config_expose_power_current_voltage(self):
        devices = [{'id':'ep25','name':'Refrigerator','manufacturer':'TP-Link','model':'EP25'}]
        entities = [
            {'device_id':'ep25','entity_id':'switch.refrigerator_2'},
            {'device_id':'ep25','entity_id':'switch.refrigerator_led','entity_category':'config'},
            {'device_id':'ep25','entity_id':'sensor.fridge_power'},
            {'device_id':'ep25','entity_id':'sensor.fridge_current'},
            {'device_id':'ep25','entity_id':'sensor.fridge_voltage'},
        ]
        values = [('sensor.fridge_power','147.9','power','W'),
                  ('sensor.fridge_current','2.00','current','A'),
                  ('sensor.fridge_voltage','117.8','voltage','V')]
        states = [{'entity_id':eid,'state':v,
                   'last_updated':'2026-10-15T01:40:00+00:00',
                   'attributes':{'device_class':kind,'unit_of_measurement':unit}}
                  for eid,v,kind,unit in values]
        result = scan(devices,entities,states)
        measured = result['devices'][0]['electrical']
        self.assertEqual(len(measured),3)
        self.assertEqual({x['kind'] for x in measured},{'power','current','voltage'})
        self.assertIn('single normal switch', result['devices'][0]['electrical_note'])

    def test_config_switch_category_from_state_can_disambiguate(self):
        devices = [{'id':'ep25','name':'Refrigerator','manufacturer':'TP-Link','model':'EP25'}]
        entities = [{'device_id':'ep25','entity_id':'switch.fridge'},
                    {'device_id':'ep25','entity_id':'switch.fridge_led'},
                    {'device_id':'ep25','entity_id':'sensor.fridge_power'}]
        states = [{'entity_id':'switch.fridge_led','state':'on',
                   'attributes':{'entity_category':'config'}},
                  {'entity_id':'sensor.fridge_power','state':'100',
                   'attributes':{'device_class':'power','unit_of_measurement':'W'}}]
        self.assertEqual(len(scan(devices,entities,states)['devices'][0]['electrical']),1)

    def test_hs300_socket_registry_child_supplies_sony_tv_measurements(self):
        devices = [
          {'id':'parent','name':'TP-LINK Power Strip 74E1','manufacturer':'TP-Link','model':'HS300'},
          {'id':'socket','name':'Kasa Sony TV Power','manufacturer':'TP-Link',
           'model':'Socket for HS300(US)','via_device_id':'parent'},
          {'id':'appliance','name':'SONY XBR-48A9S','manufacturer':'Sony'}]
        entities = [
          {'device_id':'parent','entity_id':'switch.tp_link_power_strip_74e1_kasa_sony_tv_power'},
          {'device_id':'parent','entity_id':'switch.tp_link_power_strip_74e1_kasa_roku_power'},
          {'device_id':'socket','entity_id':'sensor.socket_actual_power'},
          {'device_id':'socket','entity_id':'sensor.socket_current'},
          {'device_id':'socket','entity_id':'sensor.socket_voltage'}]
        states = [
          {'entity_id':'sensor.socket_actual_power','state':'63.6',
           'attributes':{'device_class':'power','unit_of_measurement':'W'}},
          {'entity_id':'sensor.socket_current','state':'0.59',
           'attributes':{'device_class':'current','unit_of_measurement':'A'}},
          {'entity_id':'sensor.socket_voltage','state':'118.3',
           'attributes':{'device_class':'voltage','unit_of_measurement':'V'}}]
        result = scan(devices, entities, states)
        strip = next(d for d in result['devices'] if d['model'] == 'HS300')
        sid = 'switch.tp_link_power_strip_74e1_kasa_sony_tv_power'
        self.assertEqual({v['kind'] for v in strip['outlet_meter_candidates'][sid]},
                         {'power','current','voltage'})
        self.assertEqual(strip['socket_meter_candidate_ids'], [sid])
        self.assertNotIn('switch.tp_link_power_strip_74e1_kasa_roku_power',strip['outlet_meter_candidates'])
        self.assertEqual(strip['electrical'],[])

    def test_socket_wrong_parent_or_ambiguous_not_correlated(self):
        devices = [
          {'id':'parent','name':'Strip','manufacturer':'TP-Link','model':'HS300'},
          {'id':'other','name':'Other strip','manufacturer':'TP-Link','model':'HS300'},
          {'id':'socket','name':'Kasa Sony TV Power','manufacturer':'TP-Link',
           'via_device_id':'other'}]
        entities=[
          {'device_id':'parent','entity_id':'switch.strip_kasa_sony_tv_power'},
          {'device_id':'parent','entity_id':'switch.strip_roku_power'},
          {'device_id':'socket','entity_id':'sensor.socket_voltage'}]
        states=[{'entity_id':'sensor.socket_voltage','state':'117.9',
                 'attributes':{'device_class':'voltage','unit_of_measurement':'V'}}]
        parent=next(d for d in scan(devices, entities, states)['devices'] if d['name']=='Strip')
        self.assertFalse(parent['socket_meter_candidate_ids'])
        self.assertEqual(parent['outlet_meter_candidates'],{})

    def test_hs300_unique_exact_stem_candidate(self):
        devices=[{'id':'strip','name':'Strip','manufacturer':'TP-Link','model':'HS300'}]
        entities=[
          {'device_id':'strip','entity_id':'switch.strip_roku_power'},
          {'device_id':'strip','entity_id':'switch.strip_sony_power'},
          {'device_id':'strip','entity_id':'sensor.strip_roku_power_current_consumption'},
          {'device_id':'strip','entity_id':'sensor.strip_roku_power_voltage'}]
        states=[
          {'entity_id':'sensor.strip_roku_power_current_consumption','state':'7.2',
           'attributes':{'device_class':'power','unit_of_measurement':'W'}},
          {'entity_id':'sensor.strip_roku_power_voltage','state':'118.0',
           'attributes':{'device_class':'voltage','unit_of_measurement':'V'}}]
        device=scan(devices,entities,states)['devices'][0]
        self.assertEqual(device['electrical'],[])
        matched=device['outlet_meter_candidates']
        self.assertEqual(len(matched['switch.strip_roku_power']),2)
        self.assertNotIn('switch.strip_sony_power',matched)

    def test_hs300_shared_reading_not_guessed(self):
        devices=[{'id':'strip','name':'Strip','manufacturer':'TP-Link','model':'HS300'}]
        entities=[{'device_id':'strip','entity_id':'switch.strip_roku_power'},
                  {'device_id':'strip','entity_id':'switch.strip_sony_power'},
                  {'device_id':'strip','entity_id':'sensor.strip_total_power'}]
        states=[{'entity_id':'sensor.strip_total_power','state':'123',
                 'attributes':{'device_class':'power','unit_of_measurement':'W'}}]
        self.assertEqual(scan(devices,entities,states)['devices'][0]['outlet_meter_candidates'],{})

    def test_multi_outlet_strip_does_not_attribute_shared_power(self):
        devices = [{'id':'strip','name':'Power strip','manufacturer':'TP-Link','model':'HS300'}]
        entities = [{'device_id':'strip','entity_id':'switch.outlet_one'},
                    {'device_id':'strip','entity_id':'switch.outlet_two'},
                    {'device_id':'strip','entity_id':'sensor.shared_power'}]
        states = [{'entity_id':'sensor.shared_power','state':'325',
                   'attributes':{'device_class':'power','unit_of_measurement':'W'}}]
        self.assertEqual(scan(devices, entities, states)['devices'][0]['electrical'], [])
    def test_registry_review_distinguishes_disabled_and_virtual(self):
        devices = [
            {'id':'a','name':'Fan Wind Speed Level:2','manufacturer':'tuya','model':'Scene'},
            {'id':'b','name':'Old Sense Air Pump','manufacturer':'Sense Labs, Inc.',
             'model':'Sense','disabled_by':'user'},
            {'id':'c','name':'Zigbee Coordinator','manufacturer':'Example','model':'Coordinator'},
        ]
        result = scan(devices, [{'device_id':'a','entity_id':'scene.fan_speed'},
                                {'device_id':'b','entity_id':'sensor.old','disabled_by':'user'}])
        review = {x['name']:x for x in result['registry_review']}
        self.assertEqual(review['Fan Wind Speed Level:2']['category'], 'Possible Tuya virtual scene')
        self.assertEqual(review['Fan Wind Speed Level:2']['registered_entity_count'], 1)
        self.assertEqual(review['Fan Wind Speed Level:2']['unsupported_domain_count'], 1)
        self.assertEqual(review['Old Sense Air Pump']['category'], 'Disabled registration')
        self.assertEqual(review['Old Sense Air Pump']['disabled_entity_count'], 1)
        self.assertEqual(review['Zigbee Coordinator']['category'], 'Possible infrastructure')
        self.assertEqual(result['disabled_registrations'], 1)
        self.assertEqual(result['empty_visible_registrations'], 3)
        self.assertEqual(result['displayed_devices'], 0)
        self.assertNotIn('scene.fan_speed', str(result))
        self.assertNotIn("'id': 'a'", str(result))

    def test_unclassified_empty_is_not_called_deleted(self):
        result = scan([{'id':'x','name':'Unused Accessory','manufacturer':'Unknown'}], [])
        item = result['registry_review'][0]
        self.assertEqual(item['category'], 'No registered entities')
        self.assertNotIn('deleted', str(item).lower())

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
    def test_release_metadata_is_consistent(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        config = (root / 'config.yaml').read_text()
        version_lines = [line for line in config.splitlines() if line.startswith('version: ')]
        self.assertEqual(len(version_lines), 1)
        version = version_lines[0].split(': ', 1)[1]
        self.assertRegex(version, r'^[0-9]+[.][0-9]+[.][0-9]+$')
        self.assertIn('Home Explorer v' + version, (root / 'web' / 'index.html').read_text())
        self.assertIn('## [' + version + ']', (root / 'CHANGELOG.md').read_text())
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
    def test_automation_intelligence_roles_and_coverage(self):
        devices=[{'id':'d1','name':'Fan','manufacturer':'Example'},
                 {'id':'d2','name':'Outlet','manufacturer':'Example'},
                 {'id':'d3','name':'Unused looking but not proven','manufacturer':'Example'}]
        entities=[{'device_id':'d1','entity_id':'sensor.fan_temp'},
                  {'device_id':'d2','entity_id':'switch.outlet'},
                  {'device_id':'d3','entity_id':'sensor.unlinked'}]
        configs=[{'triggers':[{'entity_id':'sensor.fan_temp'}],
                  'conditions':[{'entity_id':'sensor.fan_temp'}],
                  'actions':[{'target':{'entity_id':'switch.outlet'}}]}]
        result=scan(devices,entities,configurations=configs,attempted=2)
        intel=result['automation_intelligence']
        self.assertEqual(intel['devices_with_exact_references'],2)
        self.assertEqual(intel['devices_used_in_triggers'],1)
        self.assertEqual(intel['devices_used_in_conditions'],1)
        self.assertEqual(intel['devices_used_in_actions'],1)
        self.assertEqual(intel['devices_with_multiple_roles'],1)
        self.assertEqual(intel['devices_without_exact_references'],1)
        self.assertTrue(intel['coverage_is_partial'])
        device=next(x for x in result['devices'] if x['name']=='Fan')
        self.assertEqual(device['automation_insight']['roles'],['trigger','condition'])
        self.assertNotIn('Unused looking but not proven',intel['scope_note'])

    def test_automation_intelligence_private_reference_not_exposed(self):
        result=scan([{'id':'d1','name':'Fan'}],
                    [{'device_id':'d1','entity_id':'sensor.fan_temp'},
                     {'device_id':'d1','entity_id':'switch.secret_rule'}],
                    configurations=[{'actions':[{'target':{'entity_id':'switch.secret_rule'}}]}],
                    attempted=1)
        intel=result['automation_intelligence']
        self.assertEqual(intel['devices_with_exact_references'],0)
        self.assertFalse(intel['coverage_is_partial'])
        self.assertNotIn('secret_rule',str(result))

    def test_automation_explanation_safe_categories(self):
        devices=[{'id':'fan','name':'Fan','manufacturer':'Example'},
                 {'id':'plug','name':'Outlet','manufacturer':'Example'}]
        entities=[{'device_id':'fan','entity_id':'sensor.fan_temperature'},
                  {'device_id':'plug','entity_id':'switch.plug'}]
        configs=[{
          'alias':'Sensitive private schedule',
          'triggers':[{'platform':'numeric_state','entity_id':'sensor.fan_temperature','above':27}],
          'conditions':[{'condition':'state','entity_id':'sensor.fan_temperature','state':'secret'}],
          'actions':[{'action':'switch.turn_on','target':{'entity_id':'switch.plug'},'data':{'password':'supersecret'}}]
        }]
        result=scan(devices,entities,configurations=configs,attempted=1)
        fan=next(d for d in result['devices'] if d['name']=='Fan')
        plug=next(d for d in result['devices'] if d['name']=='Outlet')
        self.assertIn('Numeric threshold',fan['automation_explanations']['trigger'])
        self.assertIn('State change',fan['automation_explanations']['condition'])
        self.assertIn('Action target (operation not verified)',plug['automation_explanations']['action'])
        self.assertNotIn('supersecret',str(result))
        self.assertNotIn('Sensitive private schedule',str(result))
        self.assertNotIn('switch.turn_on',str(result))

    def test_automation_explanation_ignores_unreferenced_templates(self):
        result=scan([{'id':'d','name':'Fan'}],
                    [{'device_id':'d','entity_id':'sensor.fan_temperature'}],
                    configurations=[{'triggers':[{'platform':'template',
                                                  'value_template':"{{ states('sensor.fan_temperature') }}"}]}],
                    attempted=1)
        self.assertEqual(result['devices'][0]['automation_explanations'],{})

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
    def test_only_approved_home_assistant_reads(self):
        self.assertEqual(read_query('get_states'), {'type':'get_states'})
        self.assertEqual(read_query('automation/config', entity_id='automation.winter_sump'),
                         {'type':'automation/config','entity_id':'automation.winter_sump'})
        for request in ('call_service', 'config/entity_registry/update', 'script/turn_on',
                        'automation/trigger', 'config/device_registry/remove'):
            with self.assertRaises(ValueError):
                read_query(request)
        for invalid in ('switch.sump', '../automation.winter', 'automation.private-token',
                        'automation.winter sump'):
            with self.assertRaises(ValueError):
                read_query('automation/config', entity_id=invalid)
        with self.assertRaises(ValueError):
            read_query('get_states', entity_id='switch.sump')

    def test_concurrent_device_scan_is_rejected(self):
        from server import GATEWAY
        handler=Handler.__new__(Handler)
        handler.client_address=(GATEWAY, 12345)
        handler.path='/api/devices'
        handler.reply=Mock()
        self.assertTrue(SCAN_LOCK.acquire(blocking=False))
        try:
            handler.do_GET()
        finally:
            SCAN_LOCK.release()
        self.assertEqual(handler.reply.call_args.args[0], 429)

    def test_ingress_rejects_transfer_encoding_and_unapproved_api(self):
        from io import BytesIO
        from server import GATEWAY
        handler=Handler.__new__(Handler)
        handler.client_address=(GATEWAY, 12345)
        handler.path='/api/relationships'
        handler.reply=Mock()
        handler.headers={'Content-Type':'application/json','X-Home-Explorer':'relationship-update',
                         'Content-Length':'2','Transfer-Encoding':'chunked'}
        handler.rfile=BytesIO(b'{}')
        handler.do_POST()
        self.assertEqual(handler.reply.call_args.args[0], 400)
        handler.reply.reset_mock()
        handler.path='/api/call_service'
        handler.do_POST()
        self.assertEqual(handler.reply.call_args.args[0], 405)
        handler.reply.reset_mock()
        handler.path='/api/call_service'
        handler.do_GET()
        self.assertEqual(handler.reply.call_args.args[0], 404)

    def test_private_filter_avoids_common_substrings(self):
        self.assertFalse(PRIVATE_NAME.search('Wall Clock'))
        self.assertFalse(PRIVATE_NAME.search('Outdoor humidity'))
        self.assertFalse(PRIVATE_NAME.search('Building Block'))
        self.assertTrue(PRIVATE_NAME.search('Front Door'))
        self.assertTrue(PRIVATE_NAME.search('security_camera'))
        self.assertTrue(PRIVATE_NAME.search('secret_token'))

    def test_http_gateway_blocks_non_ingress_calls(self):
        handler = Handler.__new__(Handler)
        handler.client_address = ('198.51.100.17', 12345)
        handler.path = '/api/devices'
        handler.reply = Mock()
        handler.do_GET()
        self.assertEqual(handler.reply.call_args.args[0],403)
        handler.reply.reset_mock()
        handler.do_POST()
        self.assertEqual(handler.reply.call_args.args[0],403)

    def test_relationship_post_rejects_bad_header_or_size(self):
        from server import GATEWAY
        from io import BytesIO
        handler=Handler.__new__(Handler)
        handler.client_address=(GATEWAY,101)
        handler.path='/api/relationships'
        handler.reply=Mock()
        handler.headers={'Content-Type':'application/json','X-Home-Explorer':'wrong','Content-Length':'2'}
        handler.rfile=BytesIO(b'{}')
        handler.do_POST()
        self.assertEqual(handler.reply.call_args.args[0],415)
        handler.reply.reset_mock()
        handler.headers['X-Home-Explorer']='relationship-update'
        handler.headers['Content-Length']='16001'
        handler.do_POST()
        self.assertEqual(handler.reply.call_args.args[0],413)
        handler.reply.reset_mock()
        handler.headers['Content-Length']='not-an-integer'
        handler.do_POST()
        self.assertEqual(handler.reply.call_args.args[0],400)

    def test_relationship_write_cannot_call_services(self):
        from server import GATEWAY
        from io import BytesIO
        handler=Handler.__new__(Handler)
        handler.client_address=(GATEWAY,101)
        handler.path='/api/service_call'
        handler.reply=Mock()
        handler.headers={'Content-Type':'application/json','X-Home-Explorer':'relationship-update','Content-Length':'2'}
        handler.rfile=BytesIO(b'{}')
        handler.do_POST()
        self.assertEqual(handler.reply.call_args.args[0],405)

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
