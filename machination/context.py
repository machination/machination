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
from lxml import etree
from machination.logger import Logger

desired_status = None

def win_machination_path():
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
            return 'c:\Program Files\Machination'
    except:
        # Something went wrong with the registry setup
        return 'c:\Program Files\Machination'


def status_dir():
    """returns path to status dir

    usually /var/lib/machination or C:\Program Files\Machination\status"""
    return _get_dir("status")

def cache_dir():
    """returns path to cache dir

    usually /var/cache/machination or C:\Program Files\Machination\cache"""
    return _get_dir("cache")

def bin_dir():
    """returns path to bin dir

    usually /usr/bin or C:\Program Files\Machination\bin"""
    return _get_dir("bin")

def python_lib_dir():
    """returns path to python_lib dir

    usually /usr/lib/python or C:\Program Files\Machination"""
    return _get_dir("python_lib")

def log_dir():
    """returns path to log dir

    usually /var/log/machination or C:\Program Files\machination\log
    """
    return _get_dir("log")

def _get_dir(name):
    dirname = name + "_dir"
    envname = "MACHINATION_" + dirname.upper()

    # try the environment
    if envname in os.environ:
        return os.environ[envname]

    # now look to see if we've parsed the desired status file
    if(desired_status):
        # look it up in desired_status.xml
        try:
            directories = desired_status.xpath("/status/directories")[0]
        except IndexError:
            raise Exception("/status/directories element not found in '%s'"
                            % desired_status_file)
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
    if name == "status":
        return os.path.join(win_machination_path(),"status") if platname == "Win" else '/var/lib/machination'
    elif name == "cache":
        return os.path.join(win_machination_path(),"cache") if platname == "Win" else '/var/cache/machination'
    elif name == "bin":
        return os.path.join(win_machination_path(),"bin") if platname == "Win" else '/usr/bin'
    elif name == "python_lib":
        return win_machination_path() if platname == "Win" else '/usr/lib/python'
    elif name == 'log':
        return os.path.join(win_machination_path(),"log") if platname == "Win" else '/var/log/machination'

desired_status_file = os.path.join(status_dir(),"desired-status.xml")
try:
    desired_status = etree.parse(desired_status_file)
except IOError:
    raise IOError("could not find file '%s'" % desired_status_file)

logging_elts = desired_status.xpath('/status/logging')
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
