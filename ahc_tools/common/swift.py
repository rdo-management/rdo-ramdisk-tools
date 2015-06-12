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

# Mostly copied from ironic/common/swift.py

from oslo_config import cfg
from swiftclient import client as swift_client
from swiftclient import exceptions as swift_exceptions

from ahc_tools import exc

CONF = cfg.CONF


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


def list_opts():
    return [
        ('swift', SWIFT_OPTS)
    ]

CONF.register_opts(SWIFT_OPTS, group='swift')


class SwiftAPI(object):
    """API for communicating with Swift."""

    def __init__(self,
                 user=CONF.swift.username,
                 tenant_name=CONF.swift.tenant_name,
                 key=CONF.swift.password,
                 auth_url=CONF.swift.os_auth_url,
                 auth_version=CONF.swift.os_auth_version):
        """Constructor for creating a SwiftAPI object.

        :param user: the name of the user for Swift account
        :param tenant_name: the name of the tenant for Swift account
        :param key: the 'password' or key to authenticate with
        :param auth_url: the url for authentication
        :param auth_version: the version of api to use for authentication
        """
        params = {'retries': CONF.swift.max_retries,
                  'user': user,
                  'tenant_name': tenant_name,
                  'key': key,
                  'authurl': auth_url,
                  'auth_version': auth_version}

        self.connection = swift_client.Connection(**params)

    def get_object(self, object_name, container=CONF.swift.container):
        """Downloads a given object from Swift.

        :param object_name: The name of the object in Swift
        :param container: The name of the container for the object.
        :param headers: the headers for the object to pass to Swift
        :returns: Swift object
        :raises: exc.SwiftDownloadFailed, if the Swift operation fails.
        """
        try:
            _, obj = self.connection.get_object(container, object_name)
        except swift_exceptions.ClientException as e:
            raise exc.SwiftDownloadError(e.msg, object_name)

        return obj
