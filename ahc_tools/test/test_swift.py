# Copyright 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Mostly copied from ironic/tests/test_swift.py

import json
import mock

from oslo_config import cfg
from swiftclient import client as swift_client
from swiftclient import exceptions as swift_exception

from ahc_tools.common import swift
from ahc_tools import exc
from ahc_tools.test import base


CONF = cfg.CONF


@mock.patch.object(swift_client, 'Connection', autospec=True)
class SwiftTestCase(base.BaseTest):

    def setUp(self):
        super(SwiftTestCase, self).setUp()
        self.swift_exception = swift_exception.ClientException('', '')

        CONF.set_override('username', 'swift', 'swift')
        CONF.set_override('tenant_name', 'tenant', 'swift')
        CONF.set_override('password', 'password', 'swift')
        CONF.set_override('os_auth_url', 'http://authurl/v2.0', 'swift')
        CONF.set_override('os_auth_version', '2', 'swift')
        CONF.set_override('max_retries', 2, 'swift')

    def test___init__(self, connection_mock):
        swift.SwiftAPI(user=CONF.swift.username,
                       tenant_name=CONF.swift.tenant_name,
                       key=CONF.swift.password,
                       auth_url=CONF.swift.os_auth_url,
                       auth_version=CONF.swift.os_auth_version)
        params = {'retries': 2,
                  'user': 'swift',
                  'tenant_name': 'tenant',
                  'key': 'password',
                  'authurl': 'http://authurl/v2.0',
                  'auth_version': '2'}
        connection_mock.assert_called_once_with(**params)

    def test_get_object(self, connection_mock):
        swiftapi = swift.SwiftAPI(user=CONF.swift.username,
                                  tenant_name=CONF.swift.tenant_name,
                                  key=CONF.swift.password,
                                  auth_url=CONF.swift.os_auth_url,
                                  auth_version=CONF.swift.os_auth_version)
        connection_obj_mock = connection_mock.return_value

        facts = [['this', 'is', 'a', 'fact'],
                 ['this', 'is', 'another', 'fact']]
        expected_obj = json.dumps(facts)
        connection_obj_mock.get_object.return_value = ('foo', expected_obj)

        swift_obj = swiftapi.get_object('object')

        connection_obj_mock.get_object.assert_called_once_with(
            'ironic-discoverd', 'object')
        self.assertEqual(expected_obj, swift_obj)

    def test_get_object_fails(self, connection_mock):
        swiftapi = swift.SwiftAPI(user=CONF.swift.username,
                                  tenant_name=CONF.swift.tenant_name,
                                  key=CONF.swift.password,
                                  auth_url=CONF.swift.os_auth_url,
                                  auth_version=CONF.swift.os_auth_version)
        connection_obj_mock = connection_mock.return_value
        connection_obj_mock.get_object.side_effect = self.swift_exception
        self.assertRaises(exc.SwiftDownloadError, swiftapi.get_object,
                          'object')
        connection_obj_mock.get_object.assert_called_once_with(
            'ironic-discoverd', 'object')
