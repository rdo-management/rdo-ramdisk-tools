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
import json
import logging
import subprocess
import sys

import netifaces
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
    parser.add_argument('--bootif', help='PXE boot interface')
    parser.add_argument('callback_url', help='Full callback URL')
    return parser.parse_args(args)


def try_call(*cmd, **kwargs):
    if subprocess.call(cmd, **kwargs):
        LOG.warn('Command %s returned failure status, ignoring', cmd)


def try_shell(sh, **kwargs):
    strip = kwargs.pop('strip', True)
    try:
        result = subprocess.check_output(sh, shell=True, **kwargs)
    except subprocess.CalledProcessError as exc:
        LOG.warn('Shell script "%s" failed: %s, ignoring', sh, exc)
    else:
        return result.strip() if strip else result


def discover_network_interfaces(data):
    data.setdefault('interfaces', {})
    for iface in netifaces.interfaces():
        if iface.startswith('lo'):
            LOG.debug('Ignoring local network interface %s', iface)
            continue

        LOG.debug('Found network interface %s', iface)
        addrs = netifaces.ifaddresses(iface)

        try:
            mac = addrs[netifaces.AF_LINK][0]['addr']
        except (KeyError, IndexError):
            LOG.warn('No link information for interface %s in %s',
                     iface, addrs)
            continue

        try:
            ip = addrs[netifaces.AF_INET][0]['addr']
        except (KeyError, IndexError):
            LOG.debug('No IP address for interface %s', iface)
            ip = None

        data['interfaces'][iface] = {'mac': mac, 'ip': ip}

    LOG.info('Network interfaces: %s', data['interfaces'])


def discover_scheduling_properties(data):
    scripts = {
        'cpus': "grep processor /proc/cpuinfo | wc -l",
        'cpu_arch': "lscpu | grep Architecture | awk '{ print $2 }'",
    }
    for key, script in scripts.items():
        data[key] = try_shell(script)
        LOG.info('Value for %s is %s', key, data[key])

    ram_info = try_shell(
        "dmidecode --type memory | grep Size | awk '{ print $2; }'")
    total_ram = 0
    for ram_record in ram_info.split('\n'):
        try:
            total_ram += int(ram_record)
        except ValueError:
            pass
    LOG.info('Total RAM: %s', total_ram)

    # TODO(dtantsur): discover disk size


def discover_hardware(args, data):
    try_call('modprobe', 'ipmi_msghandler')
    try_call('modprobe', 'ipmi_devintf')
    try_call('modprobe', 'ipmi_si')

    data['boot_interface'] = args.bootif
    data['ipmi_address'] = try_shell(
        "ipmitool lan print | grep -e 'IP Address [^S]' | awk '{ print $4 }'")
    LOG.info('BMC IP address: %s', data['ipmi_address'])

    discover_network_interfaces(data)
    discover_scheduling_properties(data)

    # TODO(dtantsur): discover extended hardware data via 'hardware' lib
    # TODO(dtantsur): discover block devices


def call_discoverd(args, data):
    LOG.info('Posting collected data to %s', args.callback_url)
    resp = requests.post(args.callback_url, data=json.dumps(data))
    if resp.status_code >= 400:
        LOG.error('Discoverd: %s', resp.content.decode('utf-8'))
        resp.raise_for_status()


def collect_logs(args):
    pass  # TODO(dtantsur): implement


def fork_and_serve_logs(args):
    pass  # TODO(dtantsur): implement


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
    except Exception as exc:
        LOG.exception('Failed to call discoverd')
        failure = failure or True

    if failure:
        if args.daemonize_on_failure:
            fork_and_serve_logs(args)
        sys.exit(1)
