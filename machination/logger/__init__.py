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

class Logger():
    """Extends logging.handlers.SysLogHandler for Machination logging
    purposes"""

    loglist = []

    formats = {

    def __init__(self,config_elt):
        for dest in config_elt.xpath("/config/logging")[0]:
            logdef = {
                "lvl": dest.attrib["loglevel"],
                "type": dest.tag,
                "handle": getattr(self, "__%s" % dest.tag,
                                  self.__file)(dest.attrib["id"])
            }
            loglist.append(logdef)

    def __syslog(self, server):
        #FIXME: Set up syslog server connection and return handle to that
        pass

    def __file(self, filename):
        return filename

    def __write_msg(self, msg, lvl, kind, cat="")
        if not kind in ["warning", "log", "error", "debug"]:
            self.__write_msg(
                "[write_msg]: Tried to post message of unknown type"
                            + kind, 1, "error")
            return None
        
        for log in loglist:
            if lvl > log["lvl"]:
                pass
            else:
                getattr(self, "__write_%s" % log["type"],
                        self.__write_file)(msg, kind, cat)
