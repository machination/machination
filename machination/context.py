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

desired_status = None

def machination_path():
    "Returns the Machination path"

def status_dir():
    """returns path to status dir

    usually /var/lib/machination or C:\Program Files\Machination\status"""
    # try the environment
    if 'MACHINATION_STATUS_DIR' in os.environ:
        return os.environ['MACHINATION_STATUS_DIR']

    # now look to see if we've parsed the desired status file
    if(desired_status):
        # look it up in desired_status.xml
        try:
            directories = desired_status.xpath("/status/directories")[0]
        except IndexError:
            raise Exception("/status/directories element not found in '%s'"
                            % desired_status_file)
        if "status_dir" in directories.keys():
            return directories.get("status_dir")
    
    # try bootstrapping
    if 'MACHINATION_BOOTSTRAP_DIR' in os.environ:
        return os.environ['MACHINATION_BOOTSTRAP_DIR']

    # if all else fails, return the default
    if platform.system()[:3] == "Win":
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
                path = 'c:\Program Files\Machination'
        except:
            # Something went wrong with the registry setup
            path = 'c:\program files\machination'
        return os.path.join(path,"status")
    else:
        return "/var/lib/machination";

desired_status_file = os.path.join(status_dir(),"desired-status.xml")
try:
    desired_status = etree.parse(desired_status_file)
except IOError:
    raise IOError("could not find file '%s'" % desired_status_file)

def main(args):
    print(etree.tostring(config).decode('utf8'))


if __name__ == '__main__':
    main(sys.argv[1:])

del sys
