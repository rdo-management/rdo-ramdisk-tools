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

from oslo_config import cfg

EDEPLOY_OPTS = [
    cfg.StrOpt('lockname',
               default='/var/lock/edeploy.lock',
               help='Lock file for edeploy.'),
    cfg.StrOpt('configdir',
               default='/etc/ahc-tools/edeploy',
               help='Directory containing the edeploy state, .specs and .cmdb '
                    'files.'),
]


MATCH_OPTS = [
    cfg.BoolOpt('debug',
                default=False,
                help='Debug mode enabled/disabled.')
]


REPORT_OPTS = [
    cfg.BoolOpt('debug',
                default=False,
                help='Debug mode enabled/disabled.')
]


IRONIC_OPTS = [
    cfg.StrOpt('os_auth_url',
               default='',
               help='Keystone authentication endpoint for accessing Ironic'
                    'API.'),
    cfg.StrOpt('os_username',
               default='',
               help='User name for accessing Ironic API.'),
    cfg.StrOpt('os_password',
               default='',
               help='Password for accessing Ironic API.',
               secret=True),
    cfg.StrOpt('os_tenant_name',
               default='',
               help='Tenant name for accessing Ironic API.'),
]


cfg.CONF.register_opts(IRONIC_OPTS, group='ironic')
cfg.CONF.register_opts(EDEPLOY_OPTS, group='edeploy')
cfg.CONF.register_opts(MATCH_OPTS, group='match')
cfg.CONF.register_opts(REPORT_OPTS, group='report')


def list_opts():
    return [
        ('match', MATCH_OPTS),
        ('report', REPORT_OPTS),
        ('edeploy', EDEPLOY_OPTS),
        ('ironic', IRONIC_OPTS)
    ]
