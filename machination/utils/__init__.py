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

def worker_dir(name = None):
    workersdir = pkgutil.get_loader('machination.workers').filename
    if name is None:
        return workersdir
    return os.path.join(workersdir, name)

# Copy machination_path into this namespace. It shouldn't really exist in
# context, but it has to be there in order to avoid circular imports with this
# module.
# doesn't exist at all any more? (colin)
#machination_path = context.machination_path

del sys, context
