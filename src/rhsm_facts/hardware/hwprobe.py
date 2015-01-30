#
# Module to probe Hardware info from the system
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Pradeep Kilambi <pkilambi@redhat.com>
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import commands
import ethtool
import gettext
import logging
import os
import platform
import re
from subprocess import PIPE, Popen
import sys

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)


# Exception classes used by this module.
# from later versions of subprocess, but not there on 2.4, so include our version
class CalledProcessError(Exception):
    """This exception is raised when a process run by check_call() or
    check_output() returns a non-zero exit status.
    The exit status will be stored in the returncode attribute;
    check_output() will also store the output in the output attribute.
    """
    def __init__(self, returncode, cmd, output=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output

    def __str__(self):
        return "Command '%s' returned non-zero exit status %d" % (self.cmd, self.returncode)


class GenericPlatformSpecificInfoProvider(object):
    """Default provider for platform without a specific platform info provider.

    ie, all platforms except those with DMI (ie, intel platforms)"""
    def __init__(self, hardware_info, dump_file=None):
        self.info = {}

    @staticmethod
    def log_warnings():
        pass


class Hardware:

    def __init__(self, prefix=None, testing=None):
        self.allhw = {}
        # prefix to look for /sys, for testing
        self.prefix = prefix or ''
        self.testing = testing or False

        self.no_dmi_arches = ['s390x', 'ppc64', 'ppc64le', 'ppc']
        # we need this so we can decide which of the
        # arch specific code bases to follow
        self.arch = self.get_arch()

        self.platform_specific_info_provider = self.get_platform_specific_info_provider()

    def get_uname_info(self):

        uname_data = os.uname()
        uname_keys = ('uname.sysname', 'uname.nodename', 'uname.release',
                      'uname.version', 'uname.machine')
        self.unameinfo = dict(zip(uname_keys, uname_data))
        self.allhw.update(self.unameinfo)
        return self.unameinfo

    def get_release_info(self):
        distro_keys = ('distribution.name', 'distribution.version',
                       'distribution.id', 'distribution.version.modifier')
        self.releaseinfo = dict(filter(lambda (key, value): value,
            zip(distro_keys, self.get_distribution())))
        self.allhw.update(self.releaseinfo)
        return self.releaseinfo

    def _open_release(self, filename):
        return open(filename, 'r')

    # Determine which rough arch we are, so we know where to
    # look for hardware info. Also support a test mode that
    # specifies the arch
    def get_arch(self, prefix=None, testing=None):
        if self.testing and self.prefix:
            arch_file = "%s/arch" % self.prefix
            if os.access(arch_file, os.R_OK):
                try:
                    f = open(arch_file, 'r')
                except IOError:
                    return platform.machine()
                buf = f.read().strip()
                f.close()
                return buf
            return platform.machine()
        return platform.machine()

    def get_platform_specific_info_provider(self):
        """
        Return a class that can be used to get firmware info specific to
        this systems platform.

        ie, DmiFirmwareInfoProvider on intel platforms, and a EmptyInfo otherwise.
        """
        # we could potential consider /proc/sysinfo as a FirmwareInfoProvider
        # but at the moment, it is just firmware/dmi stuff.
        if self.arch in self.no_dmi_arches:
            log.debug("Not looking for DMI info since it is not available on '%s'" % self.arch)
            platform_specific_info_provider = GenericPlatformSpecificInfoProvider
        else:
            try:
                from subscription_manager import dmiinfo
                platform_specific_info_provider = dmiinfo.DmiFirmwareInfoProvider
            except ImportError:
                log.warn("Unable to load dmidecode module. No DMI info will be collected")
                platform_specific_info_provider = GenericPlatformSpecificInfoProvider

        return platform_specific_info_provider

    def get_platform_specific_info(self):
        """Read and parse data that comes from platform specific interfaces.

        This is only dmi/smbios data for now (which isn't on ppc/s390).
        """

        if self.testing and self.prefix:
            dump_file = "%s/dmi.dump" % self.prefix
            platform_info = self.platform_specific_info_provider(self.allhw, dump_file=dump_file).info
        else:
            platform_info = self.platform_specific_info_provider(self.allhw).info

        self.allhw.update(platform_info)

    # this version os very RHEL/Fedora specific...
    def get_distribution(self):

        version = 'Unknown'
        distname = 'Unknown'
        dist_id = 'Unknown'
        version_modifier = ''

        if os.path.exists('/etc/os-release'):
            f = open('/etc/os-release', 'r')
            os_release = f.readlines()
            f.close()
            data = {'PRETTY_NAME': 'Unknown',
                    'NAME': distname,
                    'ID': 'Unknown',
                    'VERSION': dist_id,
                    'VERSION_ID': version,
                    'CPE_NAME': 'Unknown'}
            for line in os_release:
                split = map(lambda piece: piece.strip('"\n '), line.split('='))
                if len(split) != 2:
                    continue
                data[split[0]] = split[1]

            version = data['VERSION_ID']
            distname = data['NAME']
            dist_id = data['VERSION']
            dist_id_search = re.search('\((.*?)\)', dist_id)
            if dist_id_search:
                dist_id = dist_id_search.group(1)
            # Split on ':' that is not preceded by '\'
            vers_mod_data = re.split('(?<!\\\):', data['CPE_NAME'])
            if len(vers_mod_data) >= 6:
                version_modifier = vers_mod_data[5].lower().replace('\\:', ':')

        elif os.path.exists('/etc/redhat-release'):
            # from platform.py from python2.
            _lsb_release_version = re.compile(r'(.+)'
                                              ' release '
                                              '([\d.]+)'
                                              '\s*(?!\()(\S*)\s*'
                                              '[^(]*(?:\((.+)\))?')
            f = self._open_release('/etc/redhat-release')
            firstline = f.readline()
            f.close()

            m = _lsb_release_version.match(firstline)

            if m is not None:
                (distname, version, tmp_modifier, dist_id) = tuple(m.groups())
                if tmp_modifier:
                    version_modifier = tmp_modifier.lower()

        elif hasattr(platform, 'linux_distribution'):
            (distname, version, dist_id) = platform.linux_distribution()
            version_modifier = 'Unknown'

        return distname, version, dist_id, version_modifier

    def get_mem_info(self):
        self.meminfo = {}

        # most of this mem info changes constantly, which makes decding
        # when to update facts painful, so lets try to just collect the
        # useful bits

        useful = ["MemTotal", "SwapTotal"]
        try:
            parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB')
            memdata = open('/proc/meminfo')
            for info in memdata:
                match = parser.match(info)
                if not match:
                    continue
                key, value = match.groups(['key', 'value'])
                if key in useful:
                    nkey = '.'.join(["memory", key.lower()])
                    self.meminfo[nkey] = "%s" % int(value)
        except Exception, e:
            print _("Error reading system memory information:"), e
        self.allhw.update(self.meminfo)
        return self.meminfo

    def get_ls_cpu_info(self):
        # if we have `lscpu`, let's use it for facts as well, under
        # the `lscpu` name space
        if not os.access('/usr/bin/lscpu', os.R_OK):
            return

        self.lscpuinfo = {}
        # let us specify a test dir of /sys info for testing
        ls_cpu_path = 'LANG=en_US.UTF-8 /usr/bin/lscpu'
        ls_cpu_cmd = ls_cpu_path

        if self.testing:
            ls_cpu_cmd = "%s -s %s" % (ls_cpu_cmd, self.prefix)
        try:
            cpudata = commands.getstatusoutput(ls_cpu_cmd)[-1].split('\n')
            for info in cpudata:
                try:
                    key, value = info.split(":")
                    nkey = '.'.join(["lscpu", key.lower().strip().replace(" ", "_")])
                    self.lscpuinfo[nkey] = "%s" % value.strip()
                except ValueError:
                    # sometimes lscpu outputs weird things. Or fails.
                    #
                    pass
        except Exception, e:
            print _("Error reading system CPU information:"), e
        self.allhw.update(self.lscpuinfo)
        return self.lscpuinfo

    def _should_get_mac_address(self, device):
        if (device.startswith('sit') or device.startswith('lo')):
            return False
        return True

    def get_network_interfaces(self):
        netinfdict = {}
        old_ipv4_metakeys = ['ipv4_address', 'ipv4_netmask', 'ipv4_broadcast']
        ipv4_metakeys = ['address', 'netmask', 'broadcast']
        ipv6_metakeys = ['address', 'netmask']
        try:
            interfaces_info = ethtool.get_interfaces_info(ethtool.get_devices())
            for info in interfaces_info:
                master = None
                mac_address = info.mac_address
                device = info.device
                # Omit mac addresses for sit and lo device types. See BZ838123
                # mac address are per interface, not per address
                if self._should_get_mac_address(device):
                    key = '.'.join(['net.interface', device, 'mac_address'])
                    netinfdict[key] = mac_address

                # all of our supported versions of python-ethtool support
                # get_ipv6_addresses
                for addr in info.get_ipv6_addresses():
                    # ethtool returns a different scope for "public" IPv6 addresses
                    # on different versions of RHEL.  EL5 is "global", while EL6 is
                    # "universe".  Make them consistent.
                    scope = addr.scope
                    if scope == 'universe':
                        scope = 'global'

                    # FIXME: this doesn't support multiple addresses per interface
                    # (it finds them, but collides on the key name and loses all
                    # but the last write). See bz #874735
                    for mkey in ipv6_metakeys:
                        key = '.'.join(['net.interface', info.device, 'ipv6_%s' % (mkey), scope])
                        # we could specify a default here... that could hide
                        # api breakage though and unit testing hw detect is... meh
                        attr = getattr(addr, mkey) or 'Unknown'
                        netinfdict[key] = attr

                # However, old version of python-ethtool do not support
                # get_ipv4_address
                #
                # python-ethtool's api changed between rhel6.3 and rhel6.4
                # (0.6-1.el6 to 0.6-2.el6)
                # (without revving the upstream version... bad python-ethtool!)
                # note that 0.6-5.el5 (from rhel5.9) has the old api
                #
                # previously, we got the 'ipv4_address' from the etherinfo object
                # directly. In the new api, that isn't exposed, so we get the list
                # of addresses on the interface, and populate the info from there.
                #
                # That api change as to address bz #759150. The bug there was that
                # python-ethtool only showed one ip address per interface. To
                # accomdate the finer grained info, the api changed...
                #
                # FIXME: see FIXME for get_ipv6_address, we don't record multiple
                # addresses per interface
                if hasattr(info, 'get_ipv4_addresses'):
                    for addr in info.get_ipv4_addresses():
                        for mkey in ipv4_metakeys:
                            # append 'ipv4_' to match the older interface and keeps facts
                            # consistent
                            key = '.'.join(['net.interface', info.device, 'ipv4_%s' % (mkey)])
                            attr = getattr(addr, mkey) or 'Unknown'
                            netinfdict[key] = attr
                # check to see if we are actually an ipv4 interface
                elif hasattr(info, 'ipv4_address'):
                    for mkey in old_ipv4_metakeys:
                        key = '.'.join(['net.interface', device, mkey])
                        attr = getattr(info, mkey) or 'Unknown'
                        netinfdict[key] = attr
                # otherwise we are ipv6 and we handled that already

                # bonded slave devices can have their hwaddr changed
                #
                # "master" here refers to the slave's master device.
                # If we find a master link, we are a  slave, and we need
                # to check the /proc/net/bonding info to see what the
                # "permanent" hw address are for this slave
                try:
                    master = os.readlink('/sys/class/net/%s/master' % info.device)
                #FIXME
                except Exception:
                    master = None

                if master:
                    master_interface = os.path.basename(master)
                    permanent_mac_addr = self._get_slave_hwaddr(master_interface, info.device)
                    key = '.'.join(['net.interface', info.device, "permanent_mac_address"])
                    netinfdict[key] = permanent_mac_addr

        except Exception:
            print _("Error reading network interface information:"), sys.exc_type
        self.allhw.update(netinfdict)
        return netinfdict

    # from rhn-client-tools  hardware.py
    # see bz#785666
    def _get_slave_hwaddr(self, master, slave):
        hwaddr = ""
        try:
            bonding = open('/proc/net/bonding/%s' % master, "r")
        except:
            return hwaddr

        slave_found = False
        for line in bonding.readlines():
            if slave_found and line.find("Permanent HW addr: ") != -1:
                hwaddr = line.split()[3].upper()
                break

            if line.find("Slave Interface: ") != -1:
                ifname = line.split()[2]
                if ifname == slave:
                    slave_found = True

        bonding.close()
        return hwaddr

    def get_virt_info(self):
        virt_dict = {}

        try:
            host_type = self._get_output('virt-what')
            # BZ1018807 xen can report xen and xen-hvm.
            # Force a single line
            host_type = ", ".join(host_type.splitlines())

            # If this is blank, then not a guest
            virt_dict['virt.is_guest'] = bool(host_type)
            if bool(host_type):
                virt_dict['virt.is_guest'] = True
                virt_dict['virt.host_type'] = host_type
            else:
                virt_dict['virt.is_guest'] = False
                virt_dict['virt.host_type'] = "Not Applicable"
        # TODO:  Should this only catch OSErrors?
        except Exception, e:
            # Otherwise there was an error running virt-what - who knows
            log.exception(e)
            virt_dict['virt.is_guest'] = 'Unknown'

        # xen dom0 is a guest for virt-what's purposes, but is a host for
        # our purposes. Adjust is_guest accordingly. (#757697)
        try:
            if virt_dict['virt.host_type'].find('dom0') > -1:
                virt_dict['virt.is_guest'] = False
        except KeyError:
            # if host_type is not defined, do nothing (#768397)
            pass

        self.allhw.update(virt_dict)
        return virt_dict

    def _get_output(self, cmd):
        log.debug("Running '%s'" % cmd)
        process = Popen([cmd], stdout=PIPE, stderr=PIPE)
        (std_output, std_error) = process.communicate()

        log.debug("%s stdout: %s" % (cmd, std_output))
        log.debug("%s stderr: %s" % (cmd, std_error))

        output = std_output.strip()

        returncode = process.poll()
        if returncode:
            raise CalledProcessError(returncode,
                                     cmd,
                                     output=output)

        return output

    def get_virt_uuid(self):
        """
        Given a populated fact list, add on a virt.uuid fact if appropriate.
        Partially adapted from Spacewalk's rhnreg.py, example hardware reporting
        found in virt-what tests
        """
        no_uuid_platforms = ['powervm_lx86', 'xen-dom0', 'ibm_systemz']

        self.allhw['virt.uuid'] = 'Unknown'

        try:
            for v in no_uuid_platforms:
                if self.allhw['virt.host_type'].find(v) > -1:
                    raise Exception(_("Virtualization platform does not support UUIDs"))
        except Exception, e:
            log.warn(_("Error finding UUID: %s"), e)
            return  # nothing more to do

        #most virt platforms record UUID via DMI/SMBIOS info.
        if 'dmi.system.uuid' in self.allhw:
            self.allhw['virt.uuid'] = self.allhw['dmi.system.uuid']

        #potentially override DMI-determined UUID with
        #what is on the file system (xen para-virt)
        try:
            uuid_file = open('/sys/hypervisor/uuid', 'r')
            uuid = uuid_file.read()
            uuid_file.close()
            self.allhw['virt.uuid'] = uuid.rstrip("\r\n")
        except IOError:
            pass

    def log_platform_firmware_warnings(self):
        "Log any warnings from firmware info gather,and/or clear them."
        self.get_platform_specific_info_provider().log_warnings()

    def get_all(self):
        hardware_methods = [self.get_uname_info,
                            self.get_release_info,
                            self.get_mem_info,
                            self.get_ls_cpu_info,
                            self.get_network_interfaces,
                            self.get_virt_info,
                            # this has to happen after everything else, since
                            # it expects to check virt and processor info
                            self.get_platform_specific_info]
        # try each hardware method, and try/except around, since
        # these tend to be fragile
        for hardware_method in hardware_methods:
            try:
                hardware_method()
            except Exception, e:
                log.warn("%s" % hardware_method)
                log.warn("Hardware detection failed: %s" % e)

        #we need to know the DMI info and VirtInfo before determining UUID.
        #Thus, we can't figure it out within the main data collection loop.
        if self.allhw.get('virt.is_guest'):
            self.get_virt_uuid()

        log.info("collected virt facts: virt.is_guest=%s, virt.host_type=%s, virt.uuid=%s",
                 self.allhw.get('virt.is_guest', 'Not Set'),
                 self.allhw.get('virt.host_type', 'Not Set'),
                 self.allhw.get('virt.uuid', 'Not Set'))

        return self.allhw


if __name__ == '__main__':
    _LIBPATH = "/usr/share/rhsm"
    # add to the path if need be
    if _LIBPATH not in sys.path:
        sys.path.append(_LIBPATH)

    from subscription_manager import logutil
    logutil.init_logger()

    hw = Hardware(prefix=sys.argv[1], testing=True)

    if len(sys.argv) > 1:
        hw.prefix = sys.argv[1]
        hw.testing = True
    hw_dict = hw.get_all()

    # just show the facts collected, unless we specify data dir and well,
    # anything else
    if len(sys.argv) > 2:
        for hkey, hvalue in sorted(hw_dict.items()):
            print "'%s' : '%s'" % (hkey, hvalue)

    if not hw.testing:
        sys.exit(0)

    # verify the cpu socket info collection we use for rhel5 matches lscpu
    cpu_items = [('cpu.core(s)_per_socket', 'lscpu.core(s)_per_socket'),
                 ('cpu.cpu(s)', 'lscpu.cpu(s)'),
                 # NOTE: the substring is different for these two folks...
                 # FIXME: follow up to see if this has changed
                 ('cpu.cpu_socket(s)', 'lscpu.socket(s)'),
                 ('cpu.book(s)', 'lscpu.book(s)'),
                 ('cpu.thread(s)_per_core', 'lscpu.thread(s)_per_core'),
                 ('cpu.socket(s)_per_book', 'lscpu.socket(s)_per_book')]
    failed = False
    failed_list = []
    for cpu_item in cpu_items:
        value_0 = int(hw_dict.get(cpu_item[0], -1))
        value_1 = int(hw_dict.get(cpu_item[1], -1))

        #print "%s/%s: %s %s" % (cpu_item[0], cpu_item[1], value_0, value_1)

        if value_0 != value_1 and ((value_0 != -1) and (value_1 != -1)):
            failed_list.append((cpu_item[0], cpu_item[1], value_0, value_1))

    must_haves = ['cpu.cpu_socket(s)', 'cpu.cpu(s)', 'cpu.core(s)_per_socket', 'cpu.thread(s)_per_core']
    missing_set = set(must_haves).difference(set(hw_dict))

    if failed:
        print "cpu detection error"
    for failed in failed_list:
        print "The values %s %s do not match (|%s| != |%s|)" % (failed[0], failed[1],
                                                                failed[2], failed[3])
    if missing_set:
        for missing in missing_set:
            print "cpu info fact: %s was missing" % missing

    if failed:
        sys.exit(1)
