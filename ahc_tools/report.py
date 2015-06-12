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

import logging
import sys

from hardware.cardiff import cardiff
from hardware.cardiff import compare_sets
from hardware.cardiff import utils as cardiff_utils
from oslo_config import cfg

from ahc_tools import conf  # noqa
from ahc_tools import utils

CONF = cfg.CONF

LOG = logging.getLogger('ahc_tools.report')

report_cli_opts = [
    cfg.BoolOpt('full',
                short='f',
                default=False,
                help='Print the full report.'),
    cfg.BoolOpt('groups',
                short='g',
                default=False,
                help='Print the groups report.'),
    cfg.BoolOpt('categories',
                short='c',
                default=False,
                help='Print the report for each category.'),
    cfg.BoolOpt('outliers',
                short='o',
                default=False,
                help='Print the report showing outliers.'),
    cfg.StrOpt('unique-id',
               dest='unique_id',
               default='uuid',
               choices=['uuid', 'serial'],
               help='Unique key to identify the nodes by.')
]


def print_report(facts):
    # The global_params are only used for a single output_dir key.
    # The output_dir key is not currently useful for this use case.
    # We could probably refactor hardware to make it a kwarg, so we don't need
    # to pass an empty dictionary.
    global_params = {}
    # The detail dictionary has three keys (group, category, item). This is
    # only used in the case that we have the print_level set to
    # utils.Levels.DETAIL
    # This is not currently used, but required by the architecture of hardware.
    detail = {'group': '', 'category': '', 'item': ''}
    # We have a different kernel cmdline for each system, so we have to ignore
    # system to get groups that have more than one system.
    ignore_list = 'system'
    # unique_id can either be 'serial' or 'uuid', in virtual environments
    # 'serial' is not reported so we default to 'uuid'
    unique_id = CONF.unique_id
    # Extract the host list from the data to get the initial list of hosts.
    systems_groups = []
    systems_groups.append(cardiff_utils.get_hosts_list(facts, unique_id))
    # Print the group information
    if CONF.groups or CONF.full:
        compare_sets.print_systems_groups(systems_groups)

    # Print the category information
    if CONF.categories or CONF.full:
        cardiff.group_systems(global_params, facts, unique_id,
                              systems_groups, ignore_list)

    # Print the outlier information
    if CONF.outliers or CONF.full:
        cardiff.compare_performance(facts, unique_id, systems_groups, detail)


def main(args=sys.argv[1:]):
    CONF.register_cli_opts(report_cli_opts)
    CONF(args=args, default_config_files=utils.DEFAULT_CONF_FILES)
    debug = CONF.report.debug
    utils.setup_logging(debug)

    # If we did not pass any print arguments, print the help and exit
    if not (CONF.groups or CONF.categories or CONF.outliers or CONF.full):
        CONF.print_help()
        LOG.error("You did not specify anything to print.")
        sys.exit(1)

    ironic_client = utils.get_ironic_client()
    nodes = ironic_client.node.list(detail=True)
    facts = [utils.get_facts(node) for node in nodes]

    print_report(facts)
