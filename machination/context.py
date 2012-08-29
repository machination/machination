#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""Store global config data.
"""

__author__ = "Bruce Duncan"
__copyright__ = "Copyright 2010, Bruce Duncan"
__licence__ = "GPL"
__version__ = "trunk"
__maintainer__ = "Bruce Duncan"
__email__ = "Bruce.Duncan@ed.ac.uk"
__status__ = "Development"


import sys
import platform
#from os.path import join
#from os import environ
import os
import io
from lxml import etree
from machination.logger import Logger
import errno

desired_status = None

def win_machination_path():
    default = os.path.join(os.environ.get('ALLUSERSPROFILE', 'C:\\ProgramData'), 'Machination')
    try:
        # look at the registry key HKLM\Software\Machination
        import wmi
        r = wmi.Registry()
        # hDefKey should be _winreg.HKLM but that doesn't work on
        # win7_64
        result, path = r.GetStringValue(
            hDefKey=2147483650,
            sSubKeyName="Software\Machination",
            sValueName="Path")
        if result:
            # Registry read failed - use default path
            # FIXME: Add syslog warning
            return default
        else:
            return path
    except:
        # Something went wrong with the registry setup
        return default


def conf_dir():
    """returns path to conf dir

    usually /etc/machination or C:\ProgramData\Machination\conf"""
    return _get_dir("conf")

def status_dir():
    """returns path to status dir

    usually /var/lib/machination or C:\ProgramData\Machination\status"""
    return _get_dir("status")


def cache_dir():
    """returns path to cache dir

    usually /var/cache/machination or C:\ProgramData\Machination\cache"""
    return _get_dir("cache")


def bin_dir():
    """returns path to bin dir

    usually /usr/bin or C:\ProgramData\Machination\bin"""
    return _get_dir("bin")


def log_dir():
    """returns path to log dir

    usually /var/log/machination or C:\ProgramData\Machination\log
    """
    return _get_dir("log")


def _get_dir(name, status_elt = None):
    dirname = name + "_dir"
    envname = "MACHINATION_" + dirname.upper()

    if status_elt == None:
        status_elt = desired_status

    # try the environment
    if envname in os.environ:
        return os.environ[envname]

    # now look to see if we've parsed the desired status file
    if(status_elt):
        # look it up in desired_status.xml
        try:
            xpath = '/status/worker[@id="__machination__"]/directories'
            directories = status_elt.xpath(xpath)[0]
        except IndexError:
            directories = etree.Element('directories')
        if name in directories.keys():
            return directories.get(name).format(dsdir=os.path.dirname(desired_status_file))

    # "status" sometimes needs bootstrapping from another location -
    # usually for debugging purposes
    if name == "status":
        if 'MACHINATION_BOOTSTRAP_DIR' in os.environ:
            return os.environ['MACHINATION_BOOTSTRAP_DIR']

    # if all else fails, return the default
    platname = platform.system()[:3]
    # ugly: a better way anyone?
    if name == "conf":
        return os.path.join(win_machination_path()) if platname == "Win" else '/etc/machination'
    elif name == "status":
        return os.path.join(win_machination_path(), "status") if platname == "Win" else '/var/lib/machination'
    elif name == "cache":
        return os.path.join(win_machination_path(), "cache") if platname == "Win" else '/var/cache/machination'
    elif name == "bin":
        progfiles = os.path.join(
            os.environ.get('PROGRAMFILES', 'C:\\Program Files'),
            'Machination'
            )
        return os.path.join(progfiles, "bin") if platname == "Win" else '/usr/bin'
    elif name == 'log':
        return os.path.join(win_machination_path(), "log") if platname == "Win" else '/var/log/machination'

def get_id(service_id):
    """Find the os_instance id to use with service 'service_id'"""
    try:
        with open(os.path.join(conf_dir(),
                               'services',
                               service_id,
                               'mid.txt')) as fd:
            mid = fd.readline().rstrip("\r\n")
    except IOError as e:
        if e.errno == errno.ENOENT:
            mid = None
        else:
            raise
    return mid

def get_worker_elt(name, status_elt = None):
    """Return worker element from desired_status."""
    if status_elt == None:
        status_elt = desired_status
    return status_elt.xpath(
        '/status/worker[@id="{}"]'.format(name)
        )[0]

desired_status_file = os.path.join(status_dir(), "desired-status.xml")
# Try loading any existing desired_status to find out how we
# should ask for a new one (:-))
try:
    desired_status = etree.parse(desired_status_file)
except IOError:
    # Uh oh - didn't work. Could be corrupt or perhaps this is
    # the first run.
    if os.path.exists(desired_status_file):
        # Corrupt: no safe path to continue
        raise
    else:
        # No desired_status: create one that update won't use,
        # but other progs will.
        desired_status = etree.parse(
            io.StringIO(
                '''
<status autoconstructed="1">
 <worker id="__machination__">
  <daemon address="" port="1313" sleeptime="10000"/>
  <logging>
   <stream id="stdout" loglevel="6"/>
  </logging>
 </worker>
</status>
'''
                )
            )
        # On Windows we need to give the location of ssl command and libs
        if platform.system() == 'Windows':
            ssl_elt = etree.fromstring('''
<openssl binary="C:\\OpenSSL-Win64\\bin\\openssl.exe"
         config="C:\\OpenSSL-Win64\\bin\\openssl.cfg"/>
'''
             )
            welt = desired_status.xpath(
                '/status/worker[@id="__machination__"]'
                )[0]
            welt.append(ssl_elt)

machination_worker_elt = get_worker_elt('__machination__')
logging_elts = machination_worker_elt.xpath(
    'logging'
    )
if not logging_elts:
    # defaults
    logging_elts = [etree.fromstring('<logging>' +
                                     '<stream id="stderr" loglevel="4"/>' +
                                     '</logging>')]
logger = Logger(logging_elts[0], log_dir())

def main(args):
    print(etree.tostring(config).decode('utf8'))


if __name__ == '__main__':
    main(sys.argv[1:])

del sys, logging_elts
