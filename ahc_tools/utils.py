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

import json
import logging
import sys

from ironicclient import client
from ironicclient.exc import AmbiguousAuthSystem
from oslo_config import cfg

from ahc_tools.common import swift

DEFAULT_CONF_FILES = ['/etc/ahc-tools/ahc-tools.conf']

CONF = cfg.CONF


def get_facts(node):
    """Get the facts stored on the Ironic DB"""
    # cardiff expects data in the form of a list of nodes
    # where each node is represented by a list of tuples
    # with each tuple representing a fact about the node
    try:
        object_name = node.extra['hardware_swift_object']
    except KeyError:
        err_msg = ("You must run introspection on the nodes before "
                   "running this tool.\n")
        sys.exit(err_msg)

    return _get_swift_facts(object_name)


def _get_swift_facts(object_name):
    swift_api = swift.SwiftAPI(user=CONF.swift.username,
                               tenant_name=CONF.swift.tenant_name,
                               key=CONF.swift.password,
                               auth_url=CONF.swift.os_auth_url,
                               auth_version=CONF.swift.os_auth_version)
    facts_blob = json.loads(swift_api.get_object(object_name))
    facts = [tuple(fact) for fact in facts_blob]
    return facts


def get_ironic_client():
    """Get Ironic client instance."""
    kwargs = {'os_password': CONF.ironic.os_password,
              'os_username': CONF.ironic.os_username,
              'os_tenant_name': CONF.ironic.os_tenant_name,
              'os_auth_url': CONF.ironic.os_auth_url}
    try:
        ironic = client.get_client(1, **kwargs)
    except AmbiguousAuthSystem:
        err_msg = ("Some credentials are missing from the [ironic] section of "
                   "the configuration. The following configuration files were "
                   "searched: (%s)." % ', '.join(CONF.config_file))
        sys.exit(err_msg)
    return ironic


def capabilities_to_dict(caps):
    """Convert the Node's capabilities into a dictionary."""
    if not caps:
        return {}
    return dict(key.split(':', 1) for key in caps.split(','))


def dict_to_capabilities(caps_dict):
    """Convert a dictionary into a string with the capabilities syntax."""
    return ','.join("%s:%s" % tpl for tpl in caps_dict.items())


def setup_logging(debug):
    """Setup the log levels."""
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    for third_party in ('urllib3.connectionpool',
                        'keystoneclient.auth',
                        'iso8601.iso8601',
                        'requests.packages.urllib3.connectionpool'):
        logging.getLogger(third_party).setLevel(logging.WARNING)
    logging.getLogger('ironicclient.common.http').setLevel(
        logging.INFO if debug else logging.ERROR)
    logging.getLogger('hardware.state').setLevel(
        logging.INFO if debug else logging.WARNING)
