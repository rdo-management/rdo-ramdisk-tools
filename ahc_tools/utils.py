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

import os
import sys

from ironicclient import client
from ironicclient.exc import AmbiguousAuthSystem


def get_facts(node):
    """Get the facts stored on the Ironic DB"""
    # cardiff expects data in the form of a list of nodes
    # where each node is represented by a list of tuples
    # with each tuple representing a fact about the node
    try:
        facts = [tuple(fact) for fact in node.extra['edeploy_facts']]
    except KeyError:
        err_msg = ("You must run introspection on the nodes before "
                   "running this tool.\n")
        sys.exit(err_msg)
    return facts


def get_ironic_client():
    """Get Ironic client instance."""
    # TODO(trown): refactor to include error handling, and inputing
    #              credentials on the command line. Might also want
    #              getpass for password input.
    kwargs = {'os_password': os.environ.get('OS_PASSWORD'),
              'os_username': os.environ.get('OS_USERNAME'),
              'os_tenant_name': os.environ.get('OS_TENANT_NAME'),
              'os_auth_url': os.environ.get('OS_AUTH_URL')}
    try:
        ironic = client.get_client(1, **kwargs)
    except AmbiguousAuthSystem:
        if kwargs['os_password']:
            kwargs['os_password'] = "<hidden>"
        err_msg = ("Some credentials are missing. The needed environment "
                   "variables are set as follows: "
                   "OS_PASSWORD=%(os_password)s, "
                   "OS_USERNAME=%(os_username)s, "
                   "OS_TENANT_NAME=%(os_tenant_name)s, "
                   "OS_AUTH_URL=%(os_auth_url)s.\n" % kwargs)
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
