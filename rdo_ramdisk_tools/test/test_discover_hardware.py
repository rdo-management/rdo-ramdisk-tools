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

import unittest

import mock

from rdo_ramdisk_tools import discover_hardware


class TestParseArgs(unittest.TestCase):
    def test(self):
        args = ['-d', 'http://url']
        parsed_args = discover_hardware.parse_args(args)
        self.assertEqual('http://url', parsed_args.callback_url)
        self.assertTrue(parsed_args.daemonize_on_failure)


def get_fake_args():
    return mock.Mock(callback_url='url', daemonize_on_failure=True)


FAKE_ARGS = get_fake_args()


@mock.patch.object(discover_hardware, 'parse_args', return_value=FAKE_ARGS)
@mock.patch.object(discover_hardware, 'fork_and_serve_logs')
@mock.patch.object(discover_hardware, 'call_discoverd')
@mock.patch.object(discover_hardware, 'collect_logs')
@mock.patch.object(discover_hardware, 'discover_hardware')
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
