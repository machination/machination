#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A machination module for logging-related functions. Machination
can log to local files relative to machination path or to syslog
servers, all of which are defined in the XML passed in to the
object at creation time.

As Machination uses two-dimensional logging (message type and level
are independent) and each log destination can have its own level
threshold, each destination is created as a separate logger. This module
handles creation and dispatching.

Retuns an object with four methods: emsg, wmsg, lmsg, and dmsg. Each logs
at the appropriate level (error, warning, info, debug) to all sources
with a loglevel > the level passed to the method. All messages are
formatted appropriately."""

__author__ = "Stew Wilson"
__copyright__ = "Copyright 2012, Stew Wilson, University of Edinburgh"
__licence__ = "GPL"
__version__ = "trunk"
__maintainer__ = "stew.wilson"
__email__ = "stew.wilson@ed.ac.uk"
__status__ = "Development"


import logging
from logging.handlers import SysLogHandler
from lxml import etree
import inspect
from machination.utils import machination_path


class Logger():
    "The core class that handles individual loggers and dispatching"

    def __init__(self, config_elt):

        # Set up module-global vars

        self.loggers = []
        self.fmtstring = "%(left)s%(lvl)s:%(modname)s.%(funct)s%(right)s"\
                ": %(message)s"

        # Assign [logger object, priority] to self.loggers for each
        # entry in /config/logging
        for dest in config_elt.xpath("/config/logging")[0]:
            if not isinstance(dest.tag, str):
                continue

            if dest.tag == "syslog":
                logger = logging.Logger(dest.attrib["id"])
                srv = (dest.attrib["id"], 514)
                hdlr = SysLogHandler(srv, SysLogHandler.LOG_LOCAL5)
                hdlr.setLevel(logging.DEBUG)
                fmt = logging.Formatter("%(asctime)s " + self.fmtstring,
                                        "%b %d %H:%M:%S")
                hdlr.setFormatter(fmt)
                logger.addHandler(hdlr)
                self.loggers.append([logger, int(dest.attrib["loglevel"])])

            elif dest.tag == "file":
                logger = logging.Logger(dest.attrib["id"])
                filepath = machination_path() + '/' + dest.attrib["id"]
                hdlr = logging.FileHandler(filepath)
                fmt = logging.Formatter(self.fmtstring)
                hdlr.setFormatter(fmt)
                logger.addHandler(hdlr)
                self.loggers.append([logger, int(dest.attrib["loglevel"])])

            else:
                # Unhandled value
                raise IOError("1", "Unknown log method " + repr(dest.tag))

    def dmsg(self, msg, lvl=6):
        "Log a debug message. Default level is 6"
        fmtdict = {"left": "[",
                   "right": "]",
                   "lvl": str(lvl),
                   "modname": inspect.stack()[1][1],
                   "funct": inspect.stack()[1][3]}
        message = msg
        self.__write_msg(lvl, "debug", message, fmtdict)

    def lmsg(self, msg, lvl=4):
        "Log an info message. Default level is 4"
        fmtdict = {"left": "(",
                   "right": ")",
                   "lvl": str(lvl),
                   "modname": inspect.stack()[1][1],
                   "funct": inspect.stack()[1][3]}
        message = msg
        self.__write_msg(lvl, "info", message, fmtdict)

    def wmsg(self, msg, lvl=1):
        "Log a warning message. Default level is 1"
        fmtdict = {"left": "{",
                   "right": "}",
                   "lvl": str(lvl),
                   "modname": inspect.stack()[1][1],
                   "funct": inspect.stack()[1][3]}
        message = "WARNING: " + msg
        self.__write_msg(lvl, "warning", message, fmtdict)

    def emsg(self, msg, lvl=1):
        "Log an error message. Default level is 1"
        fmtdict = {"left": "<",
                   "right": ">",
                   "lvl": str(lvl),
                   "modname": inspect.stack()[1][1],
                   "funct": inspect.stack()[1][3]}
        message = "ERROR: " + msg
        self.__write_msg(lvl, "debug", message, fmtdict)

    def __write_msg(self, lvl, cat, msg, fmt):
        "Dispatcher to write formatted messages to all destinations"
        for disp in self.loggers:
            if lvl > disp[1]:
                pass
            else:
                getattr(disp[0], cat)(msg, extra=fmt)
