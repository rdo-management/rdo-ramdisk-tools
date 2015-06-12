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


IRONIC_OPTS = [
    cfg.StrOpt('os_auth_url',
               default='',
               help='Keystone authentication endpoint for accessing Ironic '
                    'API. Use [keystone_authtoken]/auth_uri for keystone '
                    'authentication.'),
    cfg.StrOpt('os_username',
               default='',
               help='User name for accessing Ironic API. '
                    'Use [keystone_authtoken]/admin_user for keystone '
                    'authentication.'),
    cfg.StrOpt('os_password',
               default='',
               help='Password for accessing Ironic API. '
                    'Use [keystone_authtoken]/admin_password for keystone '
                    'authentication.',
               secret=True),
    cfg.StrOpt('os_tenant_name',
               default='',
               help='Tenant name for accessing Ironic API. '
                    'Use [keystone_authtoken]/admin_tenant_name for keystone '
                    'authentication.'),
]


SWIFT_OPTS = [
    cfg.IntOpt('max_retries',
               default=2,
               help='Maximum number of times to retry a Swift request, '
                    'before failing.'),
    cfg.IntOpt('delete_after',
               default=0,
               help='Number of seconds that the Swift object will last before '
                    'being deleted. (set to 0 to never delete the object).'),
    cfg.StrOpt('container',
               default='ironic-discoverd',
               help='Default Swift container to use when creating objects.'),
    cfg.StrOpt('username',
               default='',
               help='User name for accessing Swift API.'),
    cfg.StrOpt('password',
               default='',
               help='Password for accessing Swift API.',
               secret=True),
    cfg.StrOpt('tenant_name',
               default='',
               help='Tenant name for accessing Swift API.'),
    cfg.StrOpt('os_auth_version',
               default='2',
               help='Keystone authentication API version'),
    cfg.StrOpt('os_auth_url',
               default='',
               help='Keystone authentication URL'),
]

cfg.CONF.register_opts(SWIFT_OPTS, group='swift')
cfg.CONF.register_opts(IRONIC_OPTS, group='ironic')
cfg.CONF.register_opts(EDEPLOY_OPTS, group='edeploy')
cfg.CONF.register_opts(MATCH_OPTS, group='match')


def list_opts():
    return [
        ('match', MATCH_OPTS),
        ('edeploy', EDEPLOY_OPTS),
        ('ironic', IRONIC_OPTS),
        ('swift', SWIFT_OPTS)
    ]
