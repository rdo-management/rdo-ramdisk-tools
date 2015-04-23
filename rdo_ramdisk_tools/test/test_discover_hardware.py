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

import collections
import subprocess
import unittest

import mock
import netifaces
import requests

from rdo_ramdisk_tools import discover_hardware


class TestCommands(unittest.TestCase):
    @mock.patch.object(discover_hardware.LOG, 'warn', autospec=True)
    @mock.patch.object(subprocess, 'Popen', autospec=True)
    def test_try_call(self, mock_popen, mock_warn):
        mock_popen.return_value.communicate.return_value = ('out', 'err')
        mock_popen.return_value.returncode = 0
        discover_hardware.try_call('ls', '-l')
        mock_popen.assert_called_once_with(('ls', '-l'),
                                           stderr=subprocess.PIPE,
                                           stdout=subprocess.PIPE)
        self.assertFalse(mock_warn.called)

    @mock.patch.object(discover_hardware.LOG, 'warn', autospec=True)
    @mock.patch.object(subprocess, 'Popen', autospec=True)
    def test_try_call_fails(self, mock_popen, mock_warn):
        mock_popen.return_value.communicate.return_value = ('out', 'err')
        mock_popen.return_value.returncode = 42
        discover_hardware.try_call('ls', '-l')
        mock_popen.assert_called_once_with(('ls', '-l'),
                                           stderr=subprocess.PIPE,
                                           stdout=subprocess.PIPE)
        mock_warn.assert_called_once_with(mock.ANY, ('ls', '-l'), 42, 'err')

    @mock.patch.object(discover_hardware.LOG, 'warn', autospec=True)
    def test_try_shell(self, mock_warn):
        res = discover_hardware.try_shell('echo Hello; echo World')
        self.assertEqual('Hello\nWorld', res)
        self.assertFalse(mock_warn.called)

    @mock.patch.object(discover_hardware.LOG, 'warn', autospec=True)
    def test_try_shell_fails(self, mock_warn):
        res = discover_hardware.try_shell('exit 1')
        self.assertIsNone(res)
        self.assertTrue(mock_warn.called)

    @mock.patch.object(discover_hardware.LOG, 'warn', autospec=True)
    def test_try_shell_no_strip(self, mock_warn):
        res = discover_hardware.try_shell('echo Hello; echo World',
                                          strip=False)
        self.assertEqual('Hello\nWorld\n', res)
        self.assertFalse(mock_warn.called)


class TestParseArgs(unittest.TestCase):
    def test(self):
        args = ['-d', 'http://url']
        parsed_args = discover_hardware.parse_args(args)
        self.assertEqual('http://url', parsed_args.callback_url)
        self.assertTrue(parsed_args.daemonize_on_failure)


class TestFailures(unittest.TestCase):
    def test(self):
        f = discover_hardware.AccumulatedFailure()
        self.assertFalse(f)
        self.assertIsNone(f.get_error())
        f.add('foo')
        f.add('%s', 'bar')
        f.add(RuntimeError('baz'))
        exp = ('The following errors were encountered during '
               'hardware discovery:\n* foo\n* bar\n* baz')
        self.assertEqual(exp, f.get_error())
        self.assertTrue(f)


def get_fake_args():
    return mock.Mock(callback_url='url', daemonize_on_failure=True,
                     benchmark=None)


FAKE_ARGS = get_fake_args()


@mock.patch.object(discover_hardware, 'setup_logging', lambda args: None)
@mock.patch.object(discover_hardware, 'parse_args', return_value=FAKE_ARGS,
                   autospec=True)
@mock.patch.object(discover_hardware, 'fork_and_serve_logs', autospec=True)
@mock.patch.object(discover_hardware, 'call_discoverd', autospec=True)
@mock.patch.object(discover_hardware, 'collect_logs', autospec=True)
@mock.patch.object(discover_hardware, 'discover_hardware', autospec=True)
class TestMain(unittest.TestCase):
    def test_success(self, mock_discover, mock_logs, mock_callback,
                     mock_fork_serve, mock_parse):
        mock_logs.return_value = 'LOG'

        discover_hardware.main()

        # FIXME(dtantsur): mock does not copy arguments, so the 2nd argument
        # actually is not what we expect ({})
        mock_discover.assert_called_once_with(FAKE_ARGS, mock.ANY, mock.ANY)
        mock_logs.assert_called_once_with(FAKE_ARGS)
        mock_callback.assert_called_once_with(FAKE_ARGS, {'logs': 'LOG'},
                                              mock.ANY)
        self.assertFalse(mock_fork_serve.called)

    def test_discover_fails(self, mock_discover, mock_logs, mock_callback,
                            mock_fork_serve, mock_parse):
        mock_logs.return_value = 'LOG'
        mock_discover.side_effect = RuntimeError('boom')

        self.assertRaisesRegexp(SystemExit, '1', discover_hardware.main)

        mock_discover.assert_called_once_with(FAKE_ARGS, mock.ANY, mock.ANY)
        mock_logs.assert_called_once_with(FAKE_ARGS)
        mock_callback.assert_called_once_with(FAKE_ARGS, {'logs': 'LOG'},
                                              mock.ANY)
        failures = mock_callback.call_args[0][2]
        self.assertIn('boom', failures.get_error())
        mock_fork_serve.assert_called_once_with(FAKE_ARGS)

    def test_collect_logs_fails(self, mock_discover, mock_logs, mock_callback,
                                mock_fork_serve, mock_parse):
        mock_logs.side_effect = RuntimeError('boom')

        discover_hardware.main()

        mock_discover.assert_called_once_with(FAKE_ARGS, mock.ANY, mock.ANY)
        mock_logs.assert_called_once_with(FAKE_ARGS)
        mock_callback.assert_called_once_with(FAKE_ARGS, {}, mock.ANY)
        self.assertFalse(mock_fork_serve.called)

    def test_callback_fails(self, mock_discover, mock_logs, mock_callback,
                            mock_fork_serve, mock_parse):
        mock_logs.return_value = 'LOG'
        mock_callback.side_effect = requests.HTTPError('boom')

        self.assertRaisesRegexp(SystemExit, '1', discover_hardware.main)

        mock_discover.assert_called_once_with(FAKE_ARGS, mock.ANY, mock.ANY)
        mock_logs.assert_called_once_with(FAKE_ARGS)
        mock_callback.assert_called_once_with(FAKE_ARGS, {'logs': 'LOG'},
                                              mock.ANY)
        mock_fork_serve.assert_called_once_with(FAKE_ARGS)

    def test_callback_fails2(self, mock_discover, mock_logs, mock_callback,
                             mock_fork_serve, mock_parse):
        mock_logs.return_value = 'LOG'
        mock_callback.side_effect = RuntimeError('boom')

        self.assertRaisesRegexp(SystemExit, '1', discover_hardware.main)

        mock_discover.assert_called_once_with(FAKE_ARGS, mock.ANY, mock.ANY)
        mock_logs.assert_called_once_with(FAKE_ARGS)
        mock_callback.assert_called_once_with(FAKE_ARGS, {'logs': 'LOG'},
                                              mock.ANY)
        mock_fork_serve.assert_called_once_with(FAKE_ARGS)

    def test_no_daemonize(self, mock_discover, mock_logs, mock_callback,
                          mock_fork_serve, mock_parse):
        new_fake_args = get_fake_args()
        new_fake_args.daemonize_on_failure = None
        mock_parse.return_value = new_fake_args
        mock_logs.return_value = 'LOG'
        mock_callback.side_effect = RuntimeError('boom')

        self.assertRaisesRegexp(SystemExit, '1', discover_hardware.main)

        mock_discover.assert_called_once_with(new_fake_args, mock.ANY,
                                              mock.ANY)
        mock_logs.assert_called_once_with(new_fake_args)
        mock_callback.assert_called_once_with(new_fake_args, {'logs': 'LOG'},
                                              mock.ANY)
        self.assertFalse(mock_fork_serve.called)


class BaseDiscoverTest(unittest.TestCase):
    def setUp(self):
        super(BaseDiscoverTest, self).setUp()
        self.failures = discover_hardware.AccumulatedFailure()
        self.data = {}


@mock.patch.object(discover_hardware, 'try_shell', autospec=True)
class TestDiscoverBasicProperties(BaseDiscoverTest):
    def test(self, mock_shell):
        mock_shell.return_value = '1.2.3.4'

        discover_hardware.discover_basic_properties(
            self.data, mock.Mock(bootif='boot:if'))

        self.assertEqual({'ipmi_address': '1.2.3.4',
                          'boot_interface': 'boot:if'},
                         self.data)


@mock.patch.object(netifaces, 'ifaddresses', autospec=True)
@mock.patch.object(netifaces, 'interfaces', autospec=True)
class TestDiscoverNetworkInterfaces(BaseDiscoverTest):
    def _call(self):
        discover_hardware.discover_network_interfaces(self.data, self.failures)

    def test_nothing(self, mock_ifaces, mock_ifaddr):
        mock_ifaces.return_value = ['lo']

        self._call()

        mock_ifaces.assert_called_once_with()
        self.assertFalse(mock_ifaddr.called)
        self.assertIn('no network interfaces', self.failures.get_error())
        self.assertEqual({'interfaces': {}}, self.data)

    def test_ok(self, mock_ifaces, mock_ifaddr):
        interfaces = [
            {
                netifaces.AF_LINK: [{'addr': '11:22:33:44:55:66'}],
                netifaces.AF_INET: [{'addr': '1.2.3.4'}],
            },
            {
                netifaces.AF_LINK: [{'addr': '11:22:33:44:55:44'}],
                netifaces.AF_INET: [{'addr': '1.2.3.2'}],
            },
        ]
        mock_ifaces.return_value = ['lo', 'em1', 'em2']
        mock_ifaddr.side_effect = iter(interfaces)

        self._call()

        mock_ifaddr.assert_any_call('em1')
        mock_ifaddr.assert_any_call('em2')
        self.assertEqual(2, mock_ifaddr.call_count)
        self.assertEqual({'em1': {'mac': '11:22:33:44:55:66',
                                  'ip': '1.2.3.4'},
                          'em2': {'mac': '11:22:33:44:55:44',
                                  'ip': '1.2.3.2'}},
                         self.data['interfaces'])
        self.assertFalse(self.failures)

    def test_missing(self, mock_ifaces, mock_ifaddr):
        interfaces = [
            {
                netifaces.AF_INET: [{'addr': '1.2.3.4'}],
            },
            {
                netifaces.AF_LINK: [],
                netifaces.AF_INET: [{'addr': '1.2.3.4'}],
            },
            {
                netifaces.AF_LINK: [{'addr': '11:22:33:44:55:66'}],
                netifaces.AF_INET: [],
            },
            {
                netifaces.AF_LINK: [{'addr': '11:22:33:44:55:44'}],
            },
        ]
        mock_ifaces.return_value = ['lo', 'br0', 'br1', 'em1', 'em2']
        mock_ifaddr.side_effect = iter(interfaces)

        self._call()

        self.assertEqual(4, mock_ifaddr.call_count)
        self.assertEqual({'em1': {'mac': '11:22:33:44:55:66', 'ip': None},
                          'em2': {'mac': '11:22:33:44:55:44', 'ip': None}},
                         self.data['interfaces'])
        self.assertFalse(self.failures)


@mock.patch.object(discover_hardware, 'try_shell', autospec=True)
class TestDiscoverSchedulingProperties(BaseDiscoverTest):
    def test_ok(self, mock_shell):
        mock_shell.side_effect = iter(('2', 'x86_64', '5368709120',
                                       '1024\n1024\nno\n2048\n'))

        discover_hardware.discover_scheduling_properties(self.data,
                                                         self.failures)

        self.assertFalse(self.failures)
        self.assertEqual({'cpus': 2, 'cpu_arch': 'x86_64', 'local_gb': 4,
                          'memory_mb': 4096}, self.data)

    def test_no_ram(self, mock_shell):
        mock_shell.side_effect = iter(('2', 'x86_64', '5368709120', None))

        discover_hardware.discover_scheduling_properties(self.data,
                                                         self.failures)

        self.assertIn('failed to get RAM', self.failures.get_error())
        self.assertEqual({'cpus': 2, 'cpu_arch': 'x86_64', 'local_gb': 4,
                          'memory_mb': None}, self.data)

    def test_local_gb_too_small(self, mock_shell):
        mock_shell.side_effect = iter(('2', 'x86_64', '42',
                                       '1024\n1024\nno\n2048\n'))

        discover_hardware.discover_scheduling_properties(self.data,
                                                         self.failures)

        self.assertIn('local_gb is less than 1 GiB', self.failures.get_error())
        self.assertEqual({'cpus': 2, 'cpu_arch': 'x86_64', 'local_gb': None,
                          'memory_mb': 4096}, self.data)


@mock.patch.object(discover_hardware, 'try_call')
class TestDiscoverAdditionalProperties(BaseDiscoverTest):
    def test_ok(self, mock_call):
        mock_call.return_value = '["prop1", "prop2"]'

        discover_hardware.discover_additional_properties(
            FAKE_ARGS, self.data, self.failures)

        self.assertFalse(self.failures)
        mock_call.assert_called_once_with('hardware-detect')
        self.assertEqual(['prop1', 'prop2'], self.data['data'])

    def test_failure(self, mock_call):
        mock_call.return_value = None

        discover_hardware.discover_additional_properties(
            FAKE_ARGS, self.data, self.failures)

        self.assertIn('unable to get extended hardware properties',
                      self.failures.get_error())
        self.assertNotIn('data', self.data)

    def test_not_json(self, mock_call):
        mock_call.return_value = 'foo?'

        discover_hardware.discover_additional_properties(
            FAKE_ARGS, self.data, self.failures)

        self.assertIn('unable to get extended hardware properties',
                      self.failures.get_error())
        self.assertNotIn('data', self.data)


@mock.patch.object(discover_hardware, 'try_shell')
class TestDiscoverBlockDevices(BaseDiscoverTest):
    def test_ok(self, mock_shell):
        mock_shell.return_value = 'QM00005\nQM00006'

        discover_hardware.discover_block_devices(self.data)

        self.assertEqual({'serials': ['QM00005', 'QM00006']},
                         self.data['block_devices'])

    def test_failure(self, mock_shell):
        mock_shell.return_value = None

        discover_hardware.discover_block_devices(self.data)

        self.assertNotIn('block_devices', self.data)


@mock.patch.object(requests, 'post', autospec=True)
class TestCallDiscoverd(unittest.TestCase):
    def test_ok(self, mock_post):
        failures = discover_hardware.AccumulatedFailure()
        data = collections.OrderedDict(data=42)
        mock_post.return_value.status_code = 200

        discover_hardware.call_discoverd(FAKE_ARGS, data, failures)

        mock_post.assert_called_once_with('url',
                                          data='{"data": 42, "error": null}')

    def test_send_failure(self, mock_post):
        failures = mock.Mock(spec=discover_hardware.AccumulatedFailure)
        failures.get_error.return_value = "boom"
        data = collections.OrderedDict(data=42)
        mock_post.return_value.status_code = 200

        discover_hardware.call_discoverd(FAKE_ARGS, data, failures)

        mock_post.assert_called_once_with('url',
                                          data='{"data": 42, "error": "boom"}')

    def test_discoverd_error(self, mock_post):
        failures = discover_hardware.AccumulatedFailure()
        data = collections.OrderedDict(data=42)
        mock_post.return_value.status_code = 400

        discover_hardware.call_discoverd(FAKE_ARGS, data, failures)

        mock_post.assert_called_once_with('url',
                                          data='{"data": 42, "error": null}')
        mock_post.return_value.raise_for_status.assert_called_once_with()
