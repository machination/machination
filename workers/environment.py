#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker for setting Windows environment variables"""

from lxml import etree
import wmi
import machination

class environment():
    logger = None
    utils = None
    #Define a shorthand constant for HKLM.
    _HLKM = 2147483650
    
    def __init__(logger, utils):
        self.logger = logger
        self.utils = utils

    def do_work(work_list):
        for item in work_list:
            key = item.attrib["id"]
            if item.attrib["type"] == "multiple":
                varlist = []
                sep = item.attrib["separator"]
                for child_var in item:
                    varlist.append(child_var.attrib["id"])
                value = sep.join(varlist)
            else:
                value = item.text
            todo[key] = value
        
        self._setenv(todo)
        
    def generate_status():
        pass

    def _setenv(work_list):
        