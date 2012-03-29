#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker for setting Windows environment variables"""

from lxml import etree
import wmi
import machination
import os

class environment():
    logger = None
    #Define a shorthand constant for HKLM.
    _HLKM = 2147483650
    envloc = "system\currentcontrolset\control\session manager\environment"
    
    def __init__(self, config_elt):
        self.logger = machination.logger.Logger(config_elt)

    def do_work(self, work_list):

    def generate_status(self):
        pass

    def _setenv():
        pass
      