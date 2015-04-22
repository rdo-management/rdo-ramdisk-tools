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
               default='/var/lock/ahc-match.lock'),
    cfg.StrOpt('configdir',
               default='/etc/edeploy'),
]
MATCH_OPTS = [
    cfg.BoolOpt('debug',
                default=False,
                help='Debug mode enabled/disabled.')
]
cfg.CONF.register_opts(EDEPLOY_OPTS, group='edeploy')
cfg.CONF.register_opts(MATCH_OPTS, group='match')


def list_opts():
    return [
        ('match', MATCH_OPTS),
        ('edeploy', EDEPLOY_OPTS)
    ]
