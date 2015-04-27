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
import sys
import unittest

from ahc_tools import report

from hardware.cardiff import cardiff
from hardware.cardiff import compare_sets
from hardware.cardiff import utils
from ironicclient import client as ic_client
from ironicclient.exc import AmbiguousAuthSystem
import mock


@mock.patch.object(report, 'get_ironic_client', autospec=True)
class TestGetFacts(unittest.TestCase):
    def test_facts(self, client_mock):
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
        client = client_mock.return_value
        client.node.list.return_value = [node1, node2]
        expected = [[(u'cpu', u'logical_0', u'bogomips', u'4199.99'),
                     (u'cpu', u'logical_0', u'cache_size', u'4096KB')],
                    [(u'cpu', u'logical_0', u'bogomips', u'4098.99'),
                     (u'cpu', u'logical_0', u'cache_size', u'4096KB')]]
        facts = report.get_facts(client)
        self.assertEqual(expected, facts)

    def test_no_facts(self, client_mock):
        node1 = mock.Mock(extra={})
        node2 = mock.Mock(extra={})
        client = client_mock.return_value
        client.node.list.return_value = [node1, node2]
        err_msg = ("You must run introspection on the nodes before "
                   "running this tool.\n")
        self.assertRaisesRegexp(SystemExit, err_msg,
                                report.get_facts, client)


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
                                report.get_ironic_client, {})
        self.assertTrue(ic_mock.called)

    def test_password_hidden(self, ic_mock):
        os.environ.clear()
        os.environ['OS_PASSWORD'] = "password"
        err_msg = ("Some credentials are missing. The needed environment "
                   "variables are set as follows: OS_PASSWORD=<hidden>, "
                   "OS_USERNAME=None, OS_TENANT_NAME=None, "
                   "OS_AUTH_URL=None.\n")
        self.assertRaisesRegexp(SystemExit, err_msg,
                                report.get_ironic_client, {})
        self.assertTrue(ic_mock.called)


@mock.patch.object(utils, 'get_hosts_list', autospec=True)
@mock.patch.object(compare_sets, 'print_systems_groups', autospec=True)
@mock.patch.object(cardiff, 'group_systems', autospec=True)
@mock.patch.object(cardiff, 'compare_performance', autospec=True)
class TestPrintReport(unittest.TestCase):
    def setUp(self):
        self.args = mock.Mock()
        self.args.groups = False
        self.args.full = False
        self.args.categories = False
        self.args.outliers = False
        self.args.unique_id = 'uuid'
        self.facts = []
        self.detail = {'group': '', 'category': '', 'item': ''}

    def test_groups(self, cp_mock, gs_mock, psg_mock, ghl_mock):
        self.args.groups = True
        ghl_mock.return_value = []
        report.print_report(self.args, self.facts)
        ghl_mock.assert_called_once_with([], 'uuid')
        psg_mock.assert_called_once_with([[]])
        self.assertFalse(cp_mock.called)
        self.assertFalse(gs_mock.called)

    def test_categories(self, cp_mock, gs_mock, psg_mock, ghl_mock):
        self.args.categories = True
        ghl_mock.return_value = []
        report.print_report(self.args, self.facts)
        ghl_mock.assert_called_once_with([], 'uuid')
        gs_mock.assert_called_once_with({}, self.facts, 'uuid', [[]], 'system')
        self.assertFalse(cp_mock.called)
        self.assertFalse(psg_mock.called)

    def test_outliers(self, cp_mock, gs_mock, psg_mock, ghl_mock):
        self.args.outliers = True
        ghl_mock.return_value = []
        report.print_report(self.args, self.facts)
        ghl_mock.assert_called_once_with([], 'uuid')
        cp_mock.assert_called_once_with([], 'uuid', [[]], self.detail)
        self.assertFalse(psg_mock.called)
        self.assertFalse(gs_mock.called)

    def test_full(self, cp_mock, gs_mock, psg_mock, ghl_mock):
        self.args.full = True
        ghl_mock.return_value = []
        report.print_report(self.args, self.facts)
        ghl_mock.assert_called_once_with([], 'uuid')
        psg_mock.assert_called_once_with([[]])
        gs_mock.assert_called_once_with({}, self.facts, 'uuid', [[]], 'system')
        cp_mock.assert_called_once_with([], 'uuid', [[]], self.detail)


@mock.patch('sys.stdout')
class TestMain(unittest.TestCase):
    def test_no_args(self, out_mock):
        sys.argv = ["ironic-cardiff"]
        self.assertRaisesRegexp(SystemExit, "1", report.main)
