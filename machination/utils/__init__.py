#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""Provide utility functions useful to the Machination core and to workers.

OS-specific functions are provided in this module and imported into utils'
namespace. The code to do this is basically copied from Python's os module.

In an ideal world this would be the only OS-dependent code in Machination. In
practice, lots of the functions in this and related modules depend on the
context modules and the context module must be OS-dependent because the
location of the configuration file is. Therefore, there is also
platform-specific code there.

"""

__author__ = "Bruce Duncan"
__copyright__ = "Copyright 2012, Bruce Duncan, University of Edinburgh"
__licence__ = "GPL"
__version__ = "trunk"
__maintainer__ = "Bruce.Duncan"
__email__ = "Bruce.Duncan@ed.ac.uk"
__status__ = "Development"

import sys
import os
import pkgutil
import platform
import copy
from machination import context

__all__ = ['machination_id', 'machination_path']


def _get_exports_list(module):
    try:
        return list(module.__all__)
    except AttributeError:
        return [n for n in dir(module) if n[0] != '_']

if 'posix' in sys.builtin_module_names:
    from machination.platutils.unix import *
    import machination.platutils.unix
    __all__.extend(_get_exports_list(machination.platutils.unix))
    del machination.platutils.unix
elif 'nt' in sys.builtin_module_names:
    from machination.platutils.win import *
    import machination.platutils.win
    __all__.extend(_get_exports_list(machination.platutils.win))
    del machination.platutils.win

# Now for platform-independent stuff...


def machination_id(self, serviceid):
    """Returns the machination id for the specified serviceid."""

    try:
        xpath = "/config/services/service[@id={0}]".format(serviceid)
        return context.config.xpath(xpath)[0].attrib["mid"]
    except IndexError:
        # Xpath didn't return anything
        raise IndexError("XPath error: Could not trace machination id: {}".format(serviceid))


def worker_dir(name=None):
    if name is None:
        return workers_dir
    return os.path.join(workers_dir, name)

# Copy machination_path into this namespace. It shouldn't really exist in
# context, but it has to be there in order to avoid circular imports with this
# module.
# doesn't exist at all any more? (colin)
#machination_path = context.machination_path

# this has to be a package global to avoid something that looks like a
# circular reference error
workers_dir = os.path.dirname(pkgutil.get_loader('machination.workers').get_filename())

def os_info():
    sysname = platform.system()
    if sysname == 'Windows':
        if 'PROGRAMFILES(X86)' in os.environ:
            bitness = 64
        else:
            bitness = 32
        major = platform.win32_ver()[0]
        minor = platform.win32_ver()[2]
    elif sysname == 'Linux':
        major = platform.dist()[0]
        minor = platform.dist()[1]
        mtype = platform.machine()
        if mtype.lower() in ('x86_64', 'amd64'):
            bitness = 64
        else:
            bitness = 32

    return (sysname, major, minor, bitness)

class Version(object):
    '''Parse, store and compare version numbers'''

    def __init__(self, thing):
        '''Instantiate from string or other Version object'''
        if isinstance(thing, Version):
            self.ver = copy.copy(thing.ver)
        elif isinstance(thing, str):
            self.ver = [int(x) for x in thing.split('.')]
        else:
            raise TypeError("Don't know how to make a Version from a " +
                            type(thing))
        if len(self.ver) != 3:
            raise TypeError(
                'Version should have three dotted numbers, not ' +
                str(len(self.ver))
                )

    def __str__(self):
        return '.'.join([str(x) for x in self.ver])

    def __repr__(self):
        return "machination.utils.Version('{}')".format(self.__str__())

    def __eq__(self, other):
        for i in range(3):
            if self.ver[i] < other.ver[i]: return False
            if self.ver[i] > other.ver[i]: return False
        # equal
        return True

    def __ne__(self, other):
        for i in range(3):
            if self.ver[i] < other.ver[i]: return True
            if self.ver[i] > other.ver[i]: return True
        # equal
        return False

    def __lt__(self, other):
        for i in range(3):
            if self.ver[i] < other.ver[i]: return True
            if self.ver[i] > other.ver[i]: return False
        # equal
        return False

    def __gt__(self, other):
        for i in range(3):
            if self.ver[i] > other.ver[i]: return True
            if self.ver[i] < other.ver[i]: return False
        # equal
        return False

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)

del sys, context
