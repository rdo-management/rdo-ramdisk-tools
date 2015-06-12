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

import mock
import os

from hardware import cmdb
from hardware import state
from oslo_config import cfg

from ahc_tools import exc
from ahc_tools import match
from ahc_tools.test import base
from ahc_tools import utils

CONF = cfg.CONF


def fake_load(obj, cfg_dir):
    obj._cfg_dir = cfg_dir
    obj._data = [('hw1', '*'), ]


class MatchBase(base.BaseTest):
    def setUp(self):
        super(MatchBase, self).setUp()
        basedir = os.path.dirname(os.path.abspath(__file__))
        CONF.set_override('configdir',
                          os.path.join(basedir, 'edeploy_conf'),
                          'edeploy')
        self.uuid = '1a1a1a1a-2b2b-3c3c-4d4d-5e5e5e5e5e5e'
        self.bmc_address = '1.2.3.4'
        self.node = mock.Mock(driver='pxe_ipmitool',
                              driver_info={'ipmi_address': self.bmc_address},
                              properties={'cpu_arch': 'i386', 'local_gb': 40},
                              uuid=self.uuid,
                              power_state='power on',
                              provision_state='inspecting',
                              extra={'on_discovery': 'true'},
                              instance_uuid=None,
                              maintenance=False)
        self.facts = [
            ['network', 'eth0', 'serial', '99:99:99:99:99:99'],
            ['network', 'eth0', 'ipv4', '192.168.100.12']]


@mock.patch.object(utils, 'get_facts', autospec=True)
@mock.patch.object(state.State, 'load', fake_load)
@mock.patch.object(state.State, '_load_specs',
                   lambda o, n: [('network', '$iface', 'serial', '$mac'),
                                 ('network', '$iface', 'ipv4', '$ipv4')])
class TestMatch(MatchBase):
    def setUp(self):
        super(TestMatch, self).setUp()

    def test_match(self, mock_facts):
        mock_facts.return_value = self.facts
        node_info = {}
        match.match(self.node, node_info)
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
    def test_load_failed(self, state_mock, mock_facts):
        self.assertRaises(exc.LoadFailedError, match.match,
                          self.node, self.facts)

    @mock.patch.object(state.State, 'find_match',
                       side_effect=Exception('boom'), autospec=True)
    def test_no_match(self, find_mock, mock_facts):
        self.assertRaises(exc.MatchFailedError, match.match, self.node, {})

    def test_multiple_capabilities(self, mock_facts):
        self.node.properties['capabilities'] = 'cat:meow,profile:robin'
        node_info = {'hardware': {'profile': 'batman'}, 'edeploy_facts': []}
        node_patches = match.get_update_patches(self.node, node_info)
        self.assertIn('cat:meow', node_patches[1]['value'])
        self.assertIn('profile:batman', node_patches[1]['value'])
        # Assert the old profile is gone
        self.assertNotIn('profile:robin', node_patches[1]['value'])

    def test_no_data(self, mock_facts):
        node_info = {}
        self.assertEqual([], match.get_update_patches(self.node, node_info))

    @mock.patch.object(cmdb, 'load_cmdb')
    def test_raid_configuration_passed(self, mock_load_cmdb, mock_facts):
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
        mock_facts.return_value = self.facts
        node_info = {}
        match.match(self.node, node_info)
        self.assertIn('target_raid_configuration', node_info)

        node_patches = match.get_update_patches(self.node, node_info)
        self.assertEqual('/extra/target_raid_configuration',
                         node_patches[2]['path'])

    @mock.patch.object(cmdb, 'load_cmdb')
    def test_bios_configuration_passed(self, mock_load_cmdb, mock_facts):
        mock_load_cmdb.return_value = [
            {'bios_settings': {'ProcVirtualization': 'Disabled'}}]
        mock_facts.return_value = self.facts
        node_info = {}
        match.match(self.node, node_info)
        self.assertIn('bios_settings', node_info)

        node_patches = match.get_update_patches(self.node, node_info)
        self.assertEqual('/extra/bios_settings',
                         node_patches[2]['path'])


@mock.patch.object(match.cfg, 'ConfigParser', autospec=True)
@mock.patch.object(match, 'LOG')
@mock.patch.object(utils, 'get_ironic_client', autospec=True)
@mock.patch.object(match, '_restore_state', lambda: None)
class TestMain(MatchBase):
    def setUp(self):
        super(TestMain, self).setUp()
        self.mock_client = mock.Mock()
        self.mock_client.node.list.return_value = [self.node]

    @mock.patch.object(match, '_copy_state', side_effect=Exception('boom'))
    def test_copy_failed(self, mock_copy, mock_ic, mock_log, mock_cfg):
        mock_ic.return_value = self.mock_client
        self.assertRaises(SystemExit, match.main, args=[])
        self.assertTrue(1, mock_log.error.call_count)

    @mock.patch.object(match, 'match', autospec=True,
                       side_effect=exc.LoadFailedError('boom', '/etc/edeploy'))
    @mock.patch.object(match, '_copy_state', lambda: None)
    def test_load_failed(self, mock_match, mock_ic, mock_log, mock_cfg):
        mock_ic.return_value = self.mock_client
        self.assertRaises(SystemExit, match.main, args=[])
        self.assertTrue(1, mock_log.error.call_count)

    @mock.patch.object(match, 'get_update_patches', autospec=True)
    @mock.patch.object(match, 'match', autospec=True,
                       side_effect=exc.MatchFailedError('boom', '1234567890'))
    @mock.patch.object(match, '_copy_state', lambda: None)
    def test_match_failed(self, mock_match, mock_update, mock_ic, mock_log,
                          mock_cfg):
        mock_ic.return_value = self.mock_client
        match.main(args=[])
        self.assertEqual(2, mock_log.error.call_count)
        self.assertFalse(mock_update.called)

    @mock.patch.object(match, 'match', lambda x, y: None)
    @mock.patch.object(match, 'get_update_patches', lambda x, y: None)
    @mock.patch.object(match, '_copy_state', lambda: None)
    def test_match_success(self, mock_ic, mock_log, mock_cfg):
        mock_ic.return_value = self.mock_client
        match.main(args=[])
        self.assertFalse(mock_log.error.called)

    @mock.patch.object(match, 'match', lambda x, y: None)
    @mock.patch.object(match, 'get_update_patches', lambda x, y: None)
    @mock.patch.object(match, '_copy_state', lambda: None)
    def test_update_failed(self, mock_ic, mock_log, mock_cfg):
        self.mock_client.node.update.side_effect = Exception('boom')
        mock_ic.return_value = self.mock_client
        match.main(args=[])
        self.assertTrue(1, mock_log.error.call_count)
