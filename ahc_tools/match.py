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
import shutil

from hardware import state
from oslo_config import cfg

from ahc_tools import exc
from ahc_tools import utils


CONF = cfg.CONF

LOG = logging.getLogger("ahc_tools.match")

EDEPLOY_OPTS = [
    cfg.StrOpt('lockname',
               default='/var/lock/ahc-match.lock'),
    cfg.StrOpt('configdir',
               default='/etc/edeploy'),
]
CONF.register_opts(EDEPLOY_OPTS, group='edeploy')


def match(facts, node_info):
    sobj = None

    try:
        sobj = state.State(CONF.edeploy.lockname)
    except Exception:
        raise exc.LockFailed()

    try:
        sobj.load(CONF.edeploy.configdir)
        profile, data = sobj.find_match(facts)
    except Exception:
        sobj.unlock()
        raise exc.MatchFailed()

    data['profile'] = profile

    if 'logical_disks' in data:
        node_info['target_raid_configuration'] = {
            'logical_disks': data.pop('logical_disks')}

    if 'bios_settings' in data:
        node_info['bios_settings'] = data.pop('bios_settings')

    node_info['hardware'] = data
    sobj.save()
    sobj.unlock()


def get_update_patches(node, node_info):
    patches = []

    if 'hardware' not in node_info:
        return []

    capabilities_dict = utils.capabilities_to_dict(
        node.properties.get('capabilities'))
    capabilities_dict['profile'] = node_info['hardware']['profile']

    patches.append({'op': 'add',
                    'path': '/extra/configdrive_metadata',
                    'value': {'hardware': node_info['hardware']}})
    patches.append(
        {'op': 'add',
         'path': '/properties/capabilities',
         'value': utils.dict_to_capabilities(capabilities_dict)})

    if 'target_raid_configuration' in node_info:
        patches.append(
            {'op': 'add',
             'path': '/extra/target_raid_configuration',
             'value': node_info['target_raid_configuration']})

    if 'bios_settings' in node_info:
        patches.append(
            {'op': 'add',
             'path': '/extra/bios_settings',
             'value': node_info['bios_settings']})

    return patches


def main():
    ironic_client = utils.get_ironic_client()
    nodes = ironic_client.node.list(detail=True)
    patches = {}

    try:
        _copy_state()
    except Exception:
        pass  # TODO(trown) handle exceptions

    try:
        for node in nodes:
            facts = utils.get_facts(node)
            node_info = {}
            match(facts, node_info)
            patches[node.uuid] = get_update_patches(node, node_info)
    except Exception:
        pass  # TODO(trown) handle exceptions
    finally:
        _restore_copy()

    try:
        for node in nodes:
            ironic_client.node.update(node.uuid, patches[node.uuid])
    except Exception:
        pass  # TODO(trown) handle exceptions


def _copy_state():
    src = CONF.edeploy.configdir + '/state'
    dst = CONF.edeploy.configdir + '/state.bak'
    shutil.copyfile(src, dst)


def _restore_copy():
    src = CONF.edeploy.configdir + '/state.bak'
    dst = CONF.edeploy.configdir + '/state'
    shutil.copyfile(src, dst)
