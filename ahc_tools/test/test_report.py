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

from hardware.cardiff import cardiff
from hardware.cardiff import compare_sets
from hardware.cardiff import utils
from oslo_config import cfg

from ahc_tools import report
from ahc_tools.test import base

CONF = cfg.CONF


class ReportBase(base.BaseTest):
    def setUp(self):
        super(ReportBase, self).setUp()
        CONF.register_cli_opts(report.report_cli_opts)
        self.facts = []
        self.detail = {'group': '', 'category': '', 'item': ''}


@mock.patch.object(utils, 'get_hosts_list', autospec=True)
@mock.patch.object(compare_sets, 'print_systems_groups', autospec=True)
@mock.patch.object(cardiff, 'group_systems', autospec=True)
@mock.patch.object(cardiff, 'compare_performance', autospec=True)
class TestPrintReport(ReportBase):
    def setUp(self):
        super(TestPrintReport, self).setUp()

    def test_groups(self, cp_mock, gs_mock, psg_mock, ghl_mock):
        CONF.set_override('groups', True)
        ghl_mock.return_value = []
        report.print_report(self.facts)
        ghl_mock.assert_called_once_with([], 'uuid')
        psg_mock.assert_called_once_with([[]])
        self.assertFalse(cp_mock.called)
        self.assertFalse(gs_mock.called)

    def test_categories(self, cp_mock, gs_mock, psg_mock, ghl_mock):
        CONF.set_override('categories', True)
        ghl_mock.return_value = []
        report.print_report(self.facts)
        ghl_mock.assert_called_once_with([], 'uuid')
        gs_mock.assert_called_once_with({}, self.facts, 'uuid', [[]], 'system')
        self.assertFalse(cp_mock.called)
        self.assertFalse(psg_mock.called)

    def test_outliers(self, cp_mock, gs_mock, psg_mock, ghl_mock):
        CONF.set_override('outliers', True)
        ghl_mock.return_value = []
        report.print_report(self.facts)
        ghl_mock.assert_called_once_with([], 'uuid')
        cp_mock.assert_called_once_with([], 'uuid', [[]], self.detail)
        self.assertFalse(psg_mock.called)
        self.assertFalse(gs_mock.called)

    def test_full(self, cp_mock, gs_mock, psg_mock, ghl_mock):
        CONF.set_override('full', True)
        ghl_mock.return_value = []
        report.print_report(self.facts)
        ghl_mock.assert_called_once_with([], 'uuid')
        psg_mock.assert_called_once_with([[]])
        gs_mock.assert_called_once_with({}, self.facts, 'uuid', [[]], 'system')
        cp_mock.assert_called_once_with([], 'uuid', [[]], self.detail)


@mock.patch.object(report.cfg, 'ConfigParser', autospec=True)
@mock.patch.object(report.utils, 'get_ironic_client', autospec=True)
@mock.patch.object(report.utils, 'get_facts', autospec=True)
class TestMain(ReportBase):
    def setUp(self):
        super(TestMain, self).setUp()

    def test_no_args(self, facts_mock, ic_mock, cfg_mock):
        self.assertRaisesRegexp(SystemExit, "1", report.main, args=[])

    @mock.patch.object(report, 'print_report', autospec=True)
    def test_no_exceptions(self, print_mock, facts_mock, ic_mock, cfg_mock):
        report.main(args=['-f'])
