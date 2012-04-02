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
from os.path import join
from lxml import etree


def machination_path():
    "Returns the Machination path"
    if platform.system()[:3] == "Win":
        try:
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
    else:
        #Try/Except block handles the exists/read race condition nicely
        try:
            with open("/etc/machination") as f:
                path = f.readline()
        except IOError:
            #File doesn't exist
            path = '/opt/machination/'

    return path


config = etree.parse(join(machination_path(), 'config.xml'))


def main(args):
    print(etree.tostring(config).decode('utf8'))


if __name__ == '__main__':
    main(sys.argv[1:])

del sys, platform, join, etree
