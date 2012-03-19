#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A machination module for logging-related functions. Machination
can log to local files relative to machination path or to syslog
servers, all of which are defined in the XML passed in to the
object at creation time."""

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
from machination.utils import machination_path


class Logger():

    # Define the logger object used throughout the class
    loggers = []

    def __init__(self, config_elt):
        for dest in config_elt.xpath("/config/logging")[0]:
            if dest.tag = "syslog":
                logger = logging.Logger(dest.attrib["id"])
                srv = (dest.attrib["id"], 514)
                hdlr = SysLogHandler(srv, SysLogHandler.LOCAL5)
                hdlr.setLevel(logging.DEBUG)
                fmt = logging.Formatter("%(asctime)s
                                        %(left)s%(lvl)s:%(module)s.%(funcName)s%(right)s: %(message)s",
                                        "%b %d %H:%M:%S")
                hdlr.setFormatter(fmt)
                logger.addHandler(hdlr)
                loggers.append([logger, int(dest.attrib["loglevel"])])
            elif dest.tag = "file":
                logger = logging.Logger(dest.attrib["id"])
                filepath = machination_path() + '/' + dest.attrib["id"]
                hdlr = logging.FileHandler(filepath)
                fmt = logging.Formatter("%%(left)s%(lvl)s:%(module)s.%(funcName)s%(right)s: %(message)s")
                hdlr.setFormatter(fmt)
                logger.addHandler(hdlr)
                loggers.append([logger, int(dest.attrib["loglevel"])])
            else:
                # Unhandled value
                raise IOError(1, "Unknown value in logger configuration")


    def dmsg(self, msg, lvl):
        fmtdict = {"left": "[",
                   "right": "]"
                   "lvl": str(lvl)}
        message = msg
        self.__write_msg(self, lvl, "debug", message, fmtdict)

    def lmsg(self, msg, lvl):
        fmtdict = {"left": "(",
                   "right": ")"
                   "lvl": str(lvl)}
        message = msg
        self.__write_msg(self, lvl, "info", message, fmtdict)

    def wmsg(self, msg, lvl):
        fmtdict = {"left": "{",
                   "right": "}"
                   "lvl": str(lvl)}
        message = "WARNING: " + msg
        self.__write_msg(self, lvl, "warning", message, fmtdict)

    def emsg(self, msg, lvl):
        fmtdict = {"left": "<",
                   "right": ">"
                   "lvl": str(lvl)}
        message = "ERROR: " + msg
        self.__write_msg(self, lvl, "debug", message, fmtdict)


    def __write_msg(self, lvl, cat, msg, fmt):
        # Since we have both category and level, need to do my own
        # dispatching.

        for disp in loggers:
            if lvl > disp[0]:
                pass
            else:
                getattr(disp[1], cat)(msg, extra=fmt)

