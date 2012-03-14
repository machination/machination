#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A machination module for logging-related functions.

Machination uses syslog to the main machination server by default, with file
logging when the syslog server cannot be found. Functions defined here
handle debug, message, warn, and error messages.
"""

__author__ = "Stew Wilson"
__copyright__ = "Copyright 2012, Stew Wilson, University of Edinburgh"
__licence__ = "GPL"
__version__ = "trunk"
__maintainer__ = "stew.wilson"
__email__ = "stew.wilson@ed.ac.uk"
__status__ = "Development"

import sys
from logging.handlers import SysLogHandler

# Defauls syslog server, port, and facility:
slog_server = ("machination.see.ed.ac.uk",514)
slog_facility = SysLogHandler.LOG_LOCAL5

def enable_syslog():
    """Enables logging to syslog server defined in this function
    
    Returns handler object to syslog handler."""
    syslog_server=("machination.see.ed.ac.uk", 514)
    syslog=SysLogHandler(syslog_server,SysLogHandler.LOG_LOCAL5)
    if not syslog:
        sys.exit("Can't open syslog!")
    return syslog


