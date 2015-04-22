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

from ahc_tools import utils

from hardware import matcher
from hardware import state

EDEPLOY_DIR = '/home/stack/edeploy'
EDEPLOY_LOCK = '/var/lock/ahc-match.lock'

LOG = logging.getLogger("ahc_tools.match")


def match(facts, node_info):
    facts_copy = list(facts)
    _get_node_info(facts_copy, node_info)
    sobj = None

    try:
        sobj = state.State(EDEPLOY_LOCK)
        sobj.load(EDEPLOY_DIR)
        prof, var = sobj.find_match(facts)
        var['profile'] = prof

        if 'logical_disks' in var:
            node_info['target_raid_configuration'] = {
                'logical_disks': var.pop('logical_disks')}

        if 'bios_settings' in var:
            node_info['bios_settings'] = var.pop('bios_settings')

        node_info['hardware'] = var

    except Exception as excpt:
        LOG.warning('Unable to find a matching hardware profile: %s', excpt)
    finally:
        if sobj:
            sobj.save()
            sobj.unlock()


def get_update_patches(node, node_info):
    patches = []

    if 'hardware' in node_info:
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

        patches.append(
            {'op': 'add',
             'path': '/extra/edeploy_facts',
             'value': node_info['edeploy_facts']})

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

    _copy_state()

    for node in nodes:
        facts = utils.get_facts(node)
        node_info = {}
        match(facts, node_info)
        patches = get_update_patches(node, node_info)
        ironic_client.node.update(node.uuid, patches)

    _restore_copy()


def _copy_state():
    src = EDEPLOY_DIR + '/state'
    dst = EDEPLOY_DIR + '/state.bak'
    shutil.copyfile(src, dst)


def _restore_copy():
    src = EDEPLOY_DIR + '/state.bak'
    dst = EDEPLOY_DIR + '/state'
    shutil.copyfile(src, dst)


def _get_node_info(facts, node_info):
    matcher.match_spec(('memory', 'total', 'size', '$memory_mb'),
                       facts, node_info)
    matcher.match_spec(('cpu', 'logical', 'number', '$cpus'),
                       facts, node_info)
    matcher.match_spec(('system', 'kernel', 'arch', '$cpu_arch'),
                       facts, node_info)
    matcher.match_spec(('disk', '$disk', 'size', '$local_gb'),
                       facts, node_info)
    matcher.match_spec(('ipmi', 'lan', 'ip-address', '$ipmi_address'),
                       facts, node_info)
    node_info['interfaces'] = {}
    while True:
        info = {'ipv4': 'none'}
        if not matcher.match_spec(('network', '$iface', 'serial', '$mac'),
                                  facts, info):
            break
        matcher.match_spec(('network', info['iface'], 'ipv4', '$ipv4'),
                           facts, info)
        node_info['interfaces'][info['iface']] = {'mac': info['mac'],
                                                  'ip': info['ipv4']}

if __name__ == '__main__':
    main()
