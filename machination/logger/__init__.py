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

Returns an object with four methods: emsg, wmsg, lmsg, and dmsg. Each logs
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
import os
import sys


class Logger(object):
    "The core class that handles individual loggers and dispatching"

    def __init__(self, logging_elt, log_dir, default_loglevel=4):

        # Set up module-global vars

        self.loggers = []
        self.log_dir = log_dir
        self.default_loglevel = default_loglevel
        self.fmtstring = "%(left)s%(lvl)s:%(modname)s.%(funct)s%(right)s"\
                ": %(message)s"

        # Assign [logger object, priority] to self.loggers for each
        # entry in logging_elt

        for dest in logging_elt:
            self.add_destination(dest)

        self.lmsg('logging started')

    def add_destination(self, dest):
        """Add a logging destination to self.loggers"""
        if not isinstance(dest.tag, str):
            return

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
            filepath = os.path.join(self.log_dir,
                                    dest.attrib["id"])
            hdlr = logging.FileHandler(filepath)
            fmt = logging.Formatter(self.fmtstring)
            hdlr.setFormatter(fmt)
            logger.addHandler(hdlr)
            self.loggers.append([logger, int(dest.attrib["loglevel"])])

        elif dest.tag == "trfile":
            when = dest.get('when', 'd')
            interval = int(dest.get('interval', 1))
            backupCount = int(dest.get('backupCount', 5))
            logger = logging.Logger(dest.attrib["id"])
            filepath = os.path.join(self.log_dir,
                                    dest.attrib["id"])
            hdlr = logging.handlers.TimedRotatingFileHandler(
                filepath,
                when = when,
                interval = interval, 
                backupCount = backupCount
                )
            fmt = logging.Formatter(self.fmtstring)
            hdlr.setFormatter(fmt)
            logger.addHandler(hdlr)
            self.loggers.append([logger, int(dest.attrib["loglevel"])])

        elif dest.tag == 'stream':
            logger = logging.Logger(dest.attrib['id'])
            hdlr = logging.StreamHandler(getattr(sys,
                                                 dest.get('id',
                                                          'stderr')))
            fmt = logging.Formatter(self.fmtstring)
            hdlr.setFormatter(fmt)
            logger.addHandler(hdlr)
            self.loggers.append([logger,
                                 int(dest.get("loglevel",
                                              self.default_loglevel))
                                 ])

        else:
            # Unhandled value
            raise IOError("1", "Unknown log method " + repr(dest.tag))

    def dmsg(self, msg, lvl=6):
        "Log a debug message. Default level is 6"
        fmtdict = {"left": "[",
                   "right": "]",
                   "lvl": str(lvl)}
        message = msg
        self.__write_msg(lvl, "debug", message, fmtdict)

    def lmsg(self, msg, lvl=4):
        "Log an info message. Default level is 4"
        fmtdict = {"left": "(",
                   "right": ")",
                   "lvl": str(lvl)}
        message = msg
        self.__write_msg(lvl, "info", message, fmtdict)

    def wmsg(self, msg, lvl=1):
        "Log a warning message. Default level is 1"
        fmtdict = {"left": "{",
                   "right": "}",
                   "lvl": str(lvl)}
        message = "WARNING: " + msg
        self.__write_msg(lvl, "warning", message, fmtdict)

    def emsg(self, msg, lvl=1):
        "Log an error message. Default level is 1"
        fmtdict = {"left": "<",
                   "right": ">",
                   "lvl": str(lvl)}
        message = "ERROR: " + msg
        self.__write_msg(lvl, "debug", message, fmtdict)

    def __write_msg(self, lvl, cat, msg, fmt):
        "Dispatcher to write formatted messages to all destinations"
        framerec = inspect.stack()[2]
        try:
            fmt['modname'] = framerec[0].f_globals['__name__']
            fn = framerec[3]
            cname = self.get_class_from_frame(framerec[0])
            if cname is not None:
                fn = cname + '.' + fn
            fmt['funct'] = fn
        finally:
            del framerec
        for disp in self.loggers:
            if lvl > disp[1]:
                pass
            else:
                getattr(disp[0], cat)(msg, extra=fmt)

# from http://stackoverflow.com/questions/2203424/python-how-to-retrieve-class-information-from-a-frame-object
    def get_class_from_frame(self, f):
        try:
            class_name = f.f_locals['self'].__class__.__name__
        except KeyError:
            class_name = None
        return class_name


if __name__ == "main":
    conf_file = "/home/swilso11/machination/notes/example-config-file.xml"
    conf_path = etree.parse(conf_file)
    log_master = Logger(conf_path)
    log_master.dmsg("Test Debug Message", 5)
    log_master.lmsg("Test Log Message", 7)
    log_master.wmsg("Test Warning Message")
    log_master.emsg("Test Error Message")
