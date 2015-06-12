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
import sys

from hardware import state
from oslo_config import cfg

from ahc_tools import conf  # noqa
from ahc_tools import exc
from ahc_tools import utils


CONF = cfg.CONF

LOG = logging.getLogger('ahc_tools.match')


def match(node, node_info):
    sobj = None
    try:
        sobj = state.State(lockname=CONF.edeploy.lockname)
        sobj.load(CONF.edeploy.configdir)
    except Exception as e:
        if sobj:
            sobj.unlock()
        raise exc.LoadFailedError(e.__str__(), CONF.edeploy.configdir)

    try:
        facts = utils.get_facts(node)
        profile, data = sobj.find_match(facts)
        data['profile'] = profile

        if 'logical_disks' in data:
            node_info['target_raid_configuration'] = {
                'logical_disks': data.pop('logical_disks')}

        if 'bios_settings' in data:
            node_info['bios_settings'] = data.pop('bios_settings')

        node_info['hardware'] = data
    except Exception as e:
        raise exc.MatchFailedError(e.__str__(), node.uuid)
    finally:
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


def main(args=sys.argv[1:]):
    CONF(args=args, default_config_files=utils.DEFAULT_CONF_FILES)
    debug = CONF.match.debug
    utils.setup_logging(debug)

    ironic_client = utils.get_ironic_client()
    nodes = ironic_client.node.list(detail=True)
    patches = {}

    try:
        _copy_state()
    except Exception as e:
        err_msg = ('Failed to copy the state file: %s/state. '
                   'Error was: %s' % (CONF.edeploy.configdir, e.__str__()))
        LOG.error(err_msg)
        sys.exit()

    failed_nodes = []
    for node in nodes:
        try:
            node_info = {}
            LOG.debug('Attempting to match node %s' % node.uuid)
            match(node, node_info)
            patches[node.uuid] = get_update_patches(node, node_info)
        except exc.LoadFailedError as e:
            LOG.error(e.message)
            sys.exit()
        except exc.MatchFailedError as e:
            LOG.error(e.message)
            failed_nodes.append(node)

    if failed_nodes:
        err_msg = ('The following nodes did not match any profiles '
                   'and will not be updated: ' +
                   ','.join(node.uuid for node in failed_nodes))
        LOG.error(err_msg)
    _restore_state()

    for node in nodes:
        if node not in failed_nodes:
            try:
                ironic_client.node.update(node.uuid, patches[node.uuid])
            except Exception as e:
                err_msg = ('Failed to update node (%s). '
                           'Error was: %s' % (node.uuid, e.__str__()))
                LOG.error(err_msg)


def _copy_state():
    src = CONF.edeploy.configdir + '/state'
    dst = CONF.edeploy.configdir + '/state.bak'
    shutil.copyfile(src, dst)


def _restore_state():
    src = CONF.edeploy.configdir + '/state.bak'
    dst = CONF.edeploy.configdir + '/state'
    shutil.copyfile(src, dst)
