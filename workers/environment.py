#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker for setting Windows environment variables"""

from lxml import etree
import wmi
import machination
import os

class environment():
    logger = None
    utils = None
    #Define a shorthand constant for HKLM.
    _HLKM = 2147483650
    envloc = "system\currentcontrolset\control\session manager\environment"
    
    def __init__(logger, utils):
        self.logger = logger
        self.utils = utils

    def do_work(work_list):
        for item in work_list:
            key = item.attrib["id"]
            if item.attrib["type"] == "multiple":
                varlist = []
                sep = item.attrib["separator"]
                value = sep.join([child_var.attrib["id"] for child_var in item])
            else:
                value = item.text
            todo[key] = value
        
        self._setenv(todo)
        
    def generate_status():
        
        pass

    def _setenv(work_list):
        

      <wu id="/var[@id='key1']" op="add">
        <var id="key1">value</var>
      </wu>
      <wu id="/var[@id='list1']" op="add">
        <var id="list1" type="multiple" separator=";">
            <item id="1">foo</item>
            <item id="2">bar</item>
            <item id="3">baz</item>
        </var>
      </wu>
      <wu id="/var" op="modify">
        <NoAutoReboot>1</NoAutoReboot>
      </wu>
      <wu id="/var" op="remove">
        <NtpEnabled>1</NtpEnabled>
      </wu>
      