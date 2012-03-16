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
import inspect
class Logger():
    """Logs to all sources specified in config.xml's <logger> element tree
    Currently supports logging to local file and to sysog server.

    """

    loglist = []

    msg_formats = {
        "error": {"left": "<",
            "right": ">",
            "priority": SysLogHandler.LOG_ERR,
            "prefix": " ERROR:"},
        "debug": {"left": "[",
            "right": "]",
            "priority": SysLogHandler.LOG_DEBUG,
            "prefix": ""},
        "log": {"left": "(",
            "right": ")",
            "priority": SysLogHandler.LOG_INFO,
            "prefix": ""},
        "warning": {"left": "{",
            "right": "}",
            "priority": SysLogHandler.LOG_WARN,
            "prefix": " WARNING:"}
    }

    def __init__(self,config_elt):
        for dest in config_elt.xpath("/config/logging")[0]:
            logdef = {
                "lvl": dest.attrib["loglevel"],
                "type": dest.tag,
                "handle": getattr(self, "__%s" % dest.tag,
                                  self.__file)(dest.attrib["id"])
            }
            loglist.append(logdef)

    # To add an additional logging type "name", add two methods:
    #   __name(self, src) 
    # generates a handle (syslog server, open file object) and returns 
    # that object. Src is the id atttribute in the config statement.
    #   __write_name(self, fmesg, priority)
    # writes the formatted message fmesg to the 


    def __syslog(self, server):
        #FIXME: Set up syslog server connection and return handle to that
        pass

    def __file(self, filename):
        return filename

    def __write_syslog(self, fmesg, priority)
        pass

    def __write_file(self, fmesg, priority)
        pass

    def dmesg(self, msg, lvl)
        self.__write_msg(msg, lvl, "debug")

    def emesg(self, msg, lvl)
        self.__write_msg(msg, lvl, "error")

    def lmesg(self, msg, lvl)
        self.__write_msg(msg, lvl, "log")

    def wmesg(self, msg, lvl)
        self.__write_msg(msg, lvl, "warning") 

    def __write_msg(self, msg, lvl, kind)
        if not kind in ["warning", "log", "error", "debug"]:
            format_msg = "[write_msg]: Tried to post message of unknown type" + kind
            lvl = 1
            priority_msg = msg_formats["error"]["priority"]
        else:
            # Format message string -- inspect.stack()[1][4] gives what used
            # to be cat_prefix
            flib = msg_formats[kind]

            format_msg = flib["left"] + `lvl` + inspect.stack()[1][4] +
            flib["right"] + ":"
            pad = " " * len(format_msg)
            format_msg += flib["prefix"]
            lines = splitlines(msg)
            format_msg += lines.pop(0)
            for line in lines:
                format_msg += pad + line + "\n"

            priority_msg = flib["priority"]

        for log in loglist:
            if lvl > log["lvl"]:
                pass
            else:
                getattr(self, "__write_%s" % log["type"],
                        self.__write_file)(
                            log["handle"],
                            format_msg,
                            priority_msg)

