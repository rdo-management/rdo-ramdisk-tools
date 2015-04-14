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

import argparse
import logging
import subprocess
import sys

import requests


NAME = 'ironic-discoverd-discover-hardware'
LOG = logging.getLogger('ironic-discoverd-discover-hardware')


def parse_args(args):
    parser = argparse.ArgumentParser(description='Detect present hardware.')
    parser.add_argument('-p', '--port', type=int, default=8080,
                        help='Port to serve logs over HTTP')
    parser.add_argument('-L', '--system-log-file',
                        default='/run/initramfs/rdsosreport.txt',
                        help='Path to system log file, defaults to '
                        '/run/initramfs/rdsosreport.txt, '
                        'which is a good default for dracut ramdisks')
    parser.add_argument('-l', '--log-file', default='discovery-logs',
                        help='Path to log file, defaults to ./discovery-logs')
    parser.add_argument('-d', '--daemonize-on-failure', action='store_true',
                        help='In case of failure, fork off, continue running '
                        'and serve logs via port set by --port')
    parser.add_argument('callback-url', help='Full callback URL')
    return parser.parse_args(args)


def discover_hardware(args, data):
    pass


def call_discoverd(args, data):
    pass


def collect_logs(args):
    pass


def fork_and_serve_logs(args):
    pass


def main():
    args = parse_args(sys.argv[1:])
    data = {}
    failure = None

    try:
        discover_hardware(args, data)
    except Exception as exc:
        LOG.exception('Failed to discover data')
        failure = str(exc)
        data.setdefault('error', failure)

    try:
        data['logs'] = collect_logs(args)
    except Exception:
        LOG.exception('Failed to collect logs')

    try:
        call_discoverd(args, data)
    except Exception:
        LOG.exception('Failed to call discoverd')
        failure = failure or True

    if failure:
        if args.daemonize_on_failure:
            fork_and_serve_logs(args)
        sys.exit(1)
