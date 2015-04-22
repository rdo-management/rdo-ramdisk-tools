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

from ahc_tools import utils

from ironicclient import client as ic_client
from ironicclient.exc import AmbiguousAuthSystem
import mock


class TestGetFacts(unittest.TestCase):
    def test_facts(self):
        node1 = mock.Mock(extra={'edeploy_facts':
                                 [[u'cpu', u'logical_0',
                                   u'bogomips', u'4199.99'],
                                  [u'cpu', u'logical_0',
                                   u'cache_size', u'4096KB']
                                  ]})
        node2 = mock.Mock(extra={'edeploy_facts':
                                 [[u'cpu', u'logical_0',
                                   u'bogomips', u'4098.99'],
                                  [u'cpu', u'logical_0',
                                   u'cache_size', u'4096KB']
                                  ]})
        nodes = [node1, node2]
        expected = [[(u'cpu', u'logical_0', u'bogomips', u'4199.99'),
                     (u'cpu', u'logical_0', u'cache_size', u'4096KB')],
                    [(u'cpu', u'logical_0', u'bogomips', u'4098.99'),
                     (u'cpu', u'logical_0', u'cache_size', u'4096KB')]]
        facts = [utils.get_facts(node) for node in nodes]
        self.assertEqual(expected, facts)

    def test_no_facts(self):
        node = mock.Mock(extra={})
        err_msg = ("You must run introspection on the nodes before "
                   "running this tool.\n")
        self.assertRaisesRegexp(SystemExit, err_msg,
                                utils.get_facts, node)


@mock.patch.object(ic_client, 'get_client', autospec=True,
                   side_effect=AmbiguousAuthSystem)
class TestGetIronicClient(unittest.TestCase):
    def test_no_credentials(self, ic_mock):
        os.environ.clear()
        err_msg = ("Some credentials are missing. The needed environment "
                   "variables are set as follows: OS_PASSWORD=None, "
                   "OS_USERNAME=None, OS_TENANT_NAME=None, "
                   "OS_AUTH_URL=None.\n")
        self.assertRaisesRegexp(SystemExit, err_msg,
                                utils.get_ironic_client)
        self.assertTrue(ic_mock.called)

    def test_password_hidden(self, ic_mock):
        os.environ.clear()
        os.environ['OS_PASSWORD'] = "password"
        err_msg = ("Some credentials are missing. The needed environment "
                   "variables are set as follows: OS_PASSWORD=<hidden>, "
                   "OS_USERNAME=None, OS_TENANT_NAME=None, "
                   "OS_AUTH_URL=None.\n")
        self.assertRaisesRegexp(SystemExit, err_msg,
                                utils.get_ironic_client)
        self.assertTrue(ic_mock.called)
