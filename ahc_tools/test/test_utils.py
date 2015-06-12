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

import json
import mock

from ironicclient.exc import AmbiguousAuthSystem

from ahc_tools.test import base
from ahc_tools import utils


class TestGetFacts(base.BaseTest):
    @mock.patch.object(utils.swift, 'SwiftAPI', autospec=True)
    def test_facts(self, swift_mock):
        swift_conn = swift_mock.return_value
        obj = json.dumps([[u'cpu', u'logical_0', u'bogomips', u'4199.99'],
                          [u'cpu', u'logical_0', u'cache_size', u'4096KB']])
        swift_conn.get_object.return_value = obj
        name = 'extra_hardware-UUID1'
        node = mock.Mock(extra={'hardware_swift_object': name})
        expected = [(u'cpu', u'logical_0', u'bogomips', u'4199.99'),
                    (u'cpu', u'logical_0', u'cache_size', u'4096KB')]

        facts = utils.get_facts(node)
        self.assertEqual(expected, facts)
        swift_conn.get_object.assert_called_once_with(name)

    def test_no_facts(self):
        node = mock.Mock(extra={})
        err_msg = ("You must run introspection on the nodes before "
                   "running this tool.\n")
        self.assertRaisesRegexp(SystemExit, err_msg,
                                utils.get_facts, node)


@mock.patch.object(utils.client, 'get_client', autospec=True,
                   side_effect=AmbiguousAuthSystem)
class TestGetIronicClient(base.BaseTest):
    def test_no_credentials(self, ic_mock):
        utils.CONF.config_file = ['ahc-tools.conf']
        err_msg = '.*credentials.*missing.*ironic.*searched.*ahc-tools.conf'
        self.assertRaisesRegexp(SystemExit, err_msg,
                                utils.get_ironic_client)
        self.assertTrue(ic_mock.called)
