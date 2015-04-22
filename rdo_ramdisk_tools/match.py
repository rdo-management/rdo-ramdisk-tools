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
import shutil

from rdo_ramdisk_tools import utils

from hardware import state

EDEPLOY_DIR = '/home/stack/edeploy'


def set_profile(ironic_client, node, profile):
    capabilities_dict = utils.capabilities_to_dict(
        node.properties.get('capabilities'))
    capabilities_dict['profile'] = profile
    patch = [{'op': 'add',
              'path': '/properties/capabilities',
              'value': utils.dict_to_capabilities(capabilities_dict)}]
    ironic_client.node.update(node.uuid, patch)


def _copy_state():
    src = EDEPLOY_DIR + '/state'
    dst = EDEPLOY_DIR + '/state.bak'
    shutil.copyfile(src, dst)


def _restore_copy():
    src = EDEPLOY_DIR + '/state.bak'
    dst = EDEPLOY_DIR + '/state'
    shutil.copyfile(src, dst)


def main():
    ironic_client = utils.get_ironic_client()
    nodes = ironic_client.node.list(detail=True)

    _copy_state()
    sobj = state.State('/var/lock/match.lock')
    sobj.load(EDEPLOY_DIR)

    for node in nodes:
        if node.provision_state == 'manageable':
            profile, _ = sobj.find_match(utils.get_facts(node))
            set_profile(ironic_client, node, profile)
            sobj.save()

    _restore_copy()
    sobj.unlock()

if __name__ == '__main__':
    main()
