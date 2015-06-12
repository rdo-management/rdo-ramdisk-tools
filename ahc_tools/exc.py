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


class LoadFailedError(Exception):
    """Failure to load the edeploy state file.

    Attributes:
    o_msg -- original message from the exception that occured
    conf_dir -- directory with the state file used by edeploy
    """

    def __init__(self, o_msg, conf_dir):
        msg = ('Unable to load the state file in %s. '
               '\nERROR: %s' % (conf_dir, o_msg))
        super(LoadFailedError, self).__init__(msg)


class MatchFailedError(Exception):
    """No matching profiles were found.

    Attributes:
    o_msg -- original message from the exception that occured
    uuid -- uuid of the node that failed to match
    """

    def __init__(self, o_msg, uuid):
        msg = ('Failed to match node uuid: %s. \nERROR: %s' % (uuid, o_msg))
        super(MatchFailedError, self).__init__(msg)


class SwiftDownloadError(Exception):
    """Swift failed to download the object with hardware facts.

    Attributes:
    o_msg -- original message from the exception that occured
    object_name -- name of the Swift object that failed to download
    """

    def __init__(self, o_msg, object_name):
        msg = ('Swift failed to download the object %(object_name)s. '
               '\nERROR: %(error)s' %
               {'object_name': object_name, 'error': o_msg})
        super(SwiftDownloadError, self).__init__(msg)
