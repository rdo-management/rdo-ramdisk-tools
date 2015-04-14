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

import subprocess
import unittest

import mock
import netifaces

from rdo_ramdisk_tools import discover_hardware


class TestCommands(unittest.TestCase):
    @mock.patch.object(discover_hardware.LOG, 'warn', autospec=True)
    @mock.patch.object(subprocess, 'call', autospec=True)
    def test_try_call(self, mock_call, mock_warn):
        mock_call.return_value = 0
        discover_hardware.try_call('ls', '-l')
        mock_call.assert_called_once_with(('ls', '-l'))
        self.assertFalse(mock_warn.called)

    @mock.patch.object(discover_hardware.LOG, 'warn', autospec=True)
    @mock.patch.object(subprocess, 'call', autospec=True)
    def test_try_call_fails(self, mock_call, mock_warn):
        mock_call.return_value = 101
        discover_hardware.try_call('ls', '-l')
        mock_call.assert_called_once_with(('ls', '-l'))
        mock_warn.assert_called_once_with(mock.ANY, ('ls', '-l'))

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
    return mock.Mock(callback_url='url', daemonize_on_failure=True)


FAKE_ARGS = get_fake_args()


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


@mock.patch.object(netifaces, 'ifaddresses', autospec=True)
@mock.patch.object(netifaces, 'interfaces', autospec=True)
class TestDiscoverNetworkInterfaces(unittest.TestCase):
    def setUp(self):
        super(TestDiscoverNetworkInterfaces, self).setUp()
        self.failures = discover_hardware.AccumulatedFailure()
        self.data = {}

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
