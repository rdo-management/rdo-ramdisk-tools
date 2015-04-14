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


NAME = 'rdo-discover-hardware'
LOG = logging.getLogger(NAME)


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


class AccumulatedFailure(object):
    """Object accumulated failures without raising exception."""
    def __init__(self):
        self._failures = []

    def add(self, fail, *fmt):
        """Add failure with optional formatting."""
        if fmt:
            fail = fail % fmt
        LOG.error('Hardware discovery: %s', fail)
        self._failures.append(fail)

    def get_error(self):
        """Get error string or None."""
        if not self._failures:
            return

        msg = ('The following errors were encountered during '
               'hardware discovery:\n%s'
               % '\n'.join('* %s' % item for item in self._failures))
        return msg

    def __nonzero__(self):
        return bool(self._failures)


def discover_network_interfaces(data, failures):
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

    if data['interfaces']:
        LOG.info('Network interfaces: %s', data['interfaces'])
    else:
        failures.add('no network interfaces found')


def discover_scheduling_properties(data, failures):
    scripts = {
        'cpus': "grep processor /proc/cpuinfo | wc -l",
        'cpu_arch': "lscpu | grep Architecture | awk '{ print $2 }'",
        'local_gb': "fdisk -l | grep Disk | awk '{print $5}' | head -n 1",
    }
    for key, script in scripts.items():
        data[key] = try_shell(script)
        LOG.info('Value for %s is %s', key, data[key])

    ram_info = try_shell(
        "dmidecode --type memory | grep Size | awk '{ print $2; }'")
    if ram_info:
        total_ram = 0
        for ram_record in ram_info.split('\n'):
            try:
                total_ram += int(ram_record)
            except ValueError:
                pass
        data['memory_mb'] = total_ram
        LOG.info('Total RAM: %s', total_ram)
    else:
        failures.add('failed to get RAM information')

    for key in ('cpus', 'local_gb', 'memory_mb'):
        try:
            data[key] = int(data[key])
        except (KeyError, ValueError, TypeError):
            failures.add('Value for %s is missing or malformed: %s',
                         key, data.get(key))

    # FIXME(dtantsur): -1 is required to give Ironic some spacing for
    # partitioning and may be removed later
    if data['local_gb']:
        data['local_gb'] = data['local_gb'] / 1024 / 1024 / 1024 - 1
        if not data['local_gb']:
            failures.add('local_gb is less than 1 GiB')
            del data['local_gb']


def discover_additional_properties(args, data, failures):
    pass  # TODO(dtantsur): implement


def discover_hardware(args, data, failures):
    try_call('modprobe', 'ipmi_msghandler')
    try_call('modprobe', 'ipmi_devintf')
    try_call('modprobe', 'ipmi_si')

    # These properties might not be present, we don't count it as failure
    data['boot_interface'] = args.bootif
    data['ipmi_address'] = try_shell(
        "ipmitool lan print | grep -e 'IP Address [^S]' | awk '{ print $4 }'")
    LOG.info('BMC IP address: %s', data['ipmi_address'])

    discover_network_interfaces(data, failures)
    discover_scheduling_properties(data, failures)
    discover_additional_properties(args, data, failures)

    # TODO(dtantsur): discover block devices


def call_discoverd(args, data, failures):
    error = failures.get_error()
    data['error'] = error

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
    failures = AccumulatedFailure()

    try:
        discover_hardware(args, data, failures)
    except Exception as exc:
        LOG.exception('Failed to discover data')
        failures.add(exc)

    try:
        data['logs'] = collect_logs(args)
    except Exception:
        LOG.exception('Failed to collect logs')

    try:
        call_discoverd(args, data, failures)
    except Exception as exc:
        LOG.exception('Failed to call discoverd')
        call_error = True
    else:
        call_error = False

    if failures or call_error:
        if args.daemonize_on_failure:
            fork_and_serve_logs(args)
        sys.exit(1)
