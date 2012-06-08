#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A machination module for worker utility functions.

Most of the job done by workers is the same, with only minor differences.
This library contains utility functions necessary to do that work.

"""

__author__ = "Bruce Duncan"
__copyright__ = "Copyright 2012, Bruce Duncan, University of Edinburgh"
__licence__ = "GPL"
__version__ = "trunk"
__maintainer__ = "Bruce Duncan"
__email__ = "Bruce.Duncan@ed.ac.uk"
__status__ = "Development"

import sys
import os
import subprocess


def get_interactive_users():
    """Gets the set of logged on users"""

    pass


def is_interactive():
    """Simple truthiness boolean for when returning the full set of
    get_interactive_users() would be overkill"""
    return bool(get_interactive_users())


def runner(cmd, **kwargs):
    """Runs an arbitrary external command"""

    return subprocess.check_output(cmd)


def diskfree(disk="/"):
    """Checks free space on the specified disk"""

    stat = os.statvfs(disk)
    return stat.f_bsize * stat.f_bavail
