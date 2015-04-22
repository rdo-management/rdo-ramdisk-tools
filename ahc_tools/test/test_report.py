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
import sys
import unittest

from ahc_tools import report

from hardware.cardiff import cardiff
from hardware.cardiff import compare_sets
from hardware.cardiff import utils
import mock


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


class TestMain(unittest.TestCase):
    @mock.patch('sys.stdout')
    def test_no_args(self, out_mock):
        sys.argv = ['ahc-report']
        self.assertRaisesRegexp(SystemExit, "1", report.main)

    @mock.patch.object(report.utils, 'get_ironic_client', autospec=True)
    @mock.patch.object(report.utils, 'get_facts', autospec=True)
    @mock.patch.object(report, 'print_report', autospec=True)
    def test_no_exceptions(self, print_mock, facts_mock, ic_mock):
        with mock.patch('sys.argv', ['ahc-report', '-f']):
            report.main()
