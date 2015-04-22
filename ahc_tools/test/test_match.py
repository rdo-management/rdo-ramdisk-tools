# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import unittest

from hardware import cmdb
from hardware import state
import mock
from oslo_config import cfg

from ahc_tools import exc
from ahc_tools import match
from ahc_tools import utils

CONF = cfg.CONF


def fake_load(obj, cfg_dir):
    obj._cfg_dir = cfg_dir
    obj._data = [('hw1', '*'), ]


@mock.patch.object(state.State, 'load', fake_load)
@mock.patch.object(state.State, '_load_specs',
                   lambda o, n: [('network', '$iface', 'serial', '$mac'),
                                 ('network', '$iface', 'ipv4', '$ipv4')])
class TestMatch(unittest.TestCase):

    def setUp(self):
        super(TestMatch, self).setUp()
        basedir = os.path.dirname(os.path.abspath(__file__))
        CONF.set_override('configdir',
                          os.path.join(basedir, 'edeploy_conf'),
                          'edeploy')
        self.uuid = '1a1a1a1a-2b2b-3c3c-4d4d-5e5e5e5e5e5e'
        self.bmc_address = '1.2.3.4'
        self.macs = ['11:22:33:44:55:66', '66:55:44:33:22:11']
        self.node = mock.Mock(driver='pxe_ipmitool',
                              driver_info={'ipmi_address': self.bmc_address},
                              properties={'cpu_arch': 'i386', 'local_gb': 40},
                              uuid=self.uuid,
                              power_state='power on',
                              provision_state='inspecting',
                              extra={'on_discovery': 'true'},
                              instance_uuid=None,
                              maintenance=False)
        self.node.extra['edeploy_facts'] = [
            ['network', 'eth0', 'serial', '99:99:99:99:99:99'],
            ['network', 'eth0', 'ipv4', '192.168.100.12']]

    def test_match(self):
        facts = utils.get_facts(self.node)
        node_info = {}
        match.match(facts, node_info)
        self.assertEqual('hw1', node_info['hardware']['profile'])
        self.assertEqual('eth0', node_info['hardware']['iface'])
        self.assertEqual('99:99:99:99:99:99', node_info['hardware']['mac'])
        self.assertEqual('192.168.100.12', node_info['hardware']['ipv4'])

        node_patches = match.get_update_patches(self.node, node_info)
        self.assertEqual('/extra/configdrive_metadata',
                         node_patches[0]['path'])
        self.assertEqual('hw1',
                         node_patches[0]['value']['hardware']['profile'])
        self.assertEqual('/properties/capabilities',
                         node_patches[1]['path'])
        self.assertEqual('profile:hw1',
                         node_patches[1]['value'])

    @mock.patch.object(state.State, '__init__',
                       side_effect=Exception('boom'), autospec=True)
    def test_lock_failed(self, state_mock):
        self.assertRaises(exc.LockFailed, match.match, [], {})

    @mock.patch.object(state.State, 'find_match',
                       side_effect=Exception('boom'), autospec=True)
    def test_no_match(self, find_mock):
        self.assertRaises(exc.MatchFailed, match.match, [], {})

    def test_multiple_capabilities(self):
        self.node.properties['capabilities'] = 'cat:meow,profile:robin'
        node_info = {'hardware': {'profile': 'batman'}, 'edeploy_facts': []}
        node_patches = match.get_update_patches(self.node, node_info)
        self.assertIn('cat:meow', node_patches[1]['value'])
        self.assertIn('profile:batman', node_patches[1]['value'])
        # Assert the old profile is gone
        self.assertNotIn('profile:robin', node_patches[1]['value'])

    def test_no_data(self):
        node_info = {}
        self.assertEqual([], match.get_update_patches(self.node, node_info))

    @mock.patch.object(cmdb, 'load_cmdb')
    def test_raid_configuration_passed(self, mock_load_cmdb):
        mock_load_cmdb.return_value = [
            {'logical_disks': (
                {'disk_type': 'hdd',
                 'interface_type': 'sas',
                 'is_root_volume': 'true',
                 'raid_level': '1+0',
                 'size_gb': 50,
                 'volume_name': 'root_volume'},
                {'disk_type': 'hdd',
                 'interface_type': 'sas',
                 'number_of_physical_disks': 3,
                 'raid_level': '5',
                 'size_gb': 100,
                 'volume_name': 'data_volume'})}]
        facts = [
            ['network', 'eth0', 'serial', '99:99:99:99:99:99'],
            ['network', 'eth0', 'ipv4', '192.168.100.12'],
        ]
        node_info = {}
        match.match(facts, node_info)
        self.assertIn('target_raid_configuration', node_info)

        node_patches = match.get_update_patches(self.node, node_info)
        self.assertEqual('/extra/target_raid_configuration',
                         node_patches[2]['path'])

    @mock.patch.object(cmdb, 'load_cmdb')
    def test_bios_configuration_passed(self, mock_load_cmdb):
        mock_load_cmdb.return_value = [
            {'bios_settings': {'ProcVirtualization': 'Disabled'}}]
        facts = [
            ['network', 'eth0', 'serial', '99:99:99:99:99:99'],
            ['network', 'eth0', 'ipv4', '192.168.100.12'],
        ]
        node_info = {}
        match.match(facts, node_info)
        self.assertIn('bios_settings', node_info)

        node_patches = match.get_update_patches(self.node, node_info)
        self.assertEqual('/extra/bios_settings',
                         node_patches[2]['path'])
