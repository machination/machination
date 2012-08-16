#!/usr/bin/python
# vim: set fileencoding=utf-8:

"A worker for setting Windows environment variables"

from lxml import etree
import wmi
from machination import context
import os


class worker(object):
    "Manipulates environment variables in Windows."

    #Define a shorthand constant for HKLM.
    __HKLM = 2147483650
    envloc = "system\currentcontrolset\control\session manager\environment"

    # Define methods used to access registry values based on type.
    methods = {1: "String",
               2: "ExpandedString",
               3: "Binary",
               4: "DWORD",
               7: "MultiString"}

    # Define known multiple-value vars along with their separators
    # In future, this may come from a config element rather than
    # being hard-coded
    multi_vars = {"PATH": ";",
                  "PATHEXT": ";",
                  "TZ": ","}

    def __init__(self):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')
        self.r = wmi.Registry()

    def do_work(self, work_list):
        "Process the work units and return their status."
        result = []
        for wu in work_list:
            operator = "__{}".format(wu.attrib["op"])
            res = getattr(self, operator)(wu)
            result.append(res)
        return result

    def __add(self, work):
        "Add new environment variables."
        varname = work[1].attrib["id"]
        if work[1].attrib["type"]:
            # It's a multipart variable
            sep = work[1].attrib["separator"]
            val = sep.join([item.text for item in work[1].iter("item")])
            val = unicode(val, 'utf-8')
        else:
            val = unicode(work[1].text, 'utf-8')

        # For convenience sake, all variables are stored as REG_EXPAND_SZ
        result = r.SetExpandedStringValue(hDefKey=self.__HKLM,
                                  sSubKeyName=self.envloc,
                                  sValueName=varname,
                                  sValue=val)

        res = etree.Element("wu",
                            id=work.attrib["id"])
        if result:
            msg = "Could not set {0} to {1}".format(varname, val)
            ext_msg = msg + "Error code: {}".format(result)
            context.emsg(message)
            context.dmsg(ext_msg)
            res.attrib["status"] = "error"
            res.attrib["message"] = ext_msg
        else:
            res.attrib["status"] = "success"
        return res

    def __datamod(self, work):
        "Change existing environment variables"
        # Given that modifications to multi-vars are done in statuscompare
        # as <var> is the wu-tag, for registry entries, modify == add.
        return self.__add(work)

    def __deepmod(self, work):
        "Change existing environment variables"
        # Given that modifications to multi-vars are done in statuscompare
        # as <var> is the wu-tag, for registry entries, modify == add.
        return self.__add(work)

    def __move(self, work):
        pass

    def __remove(self, work):
        "Remove unwanted variables"
        # If we don't have notpres=1, it's an environment var that Machination
        # doesn't care about, so we just report a success
        if not work[1].attrib["notpres"]:
            res = etree.Element("wu", id=work.attrib["id"], status="success")
            return res

        # Since we actually care about it, get the variable name from the
        # XML passed as part of the wu
        varname = work[1].attrib["id"]
        result = r.DeleteValue(hDefKey=self.__HKLM,
                               sSubKeyName=self.envloc,
                               sValueName=varname)
        res = etree.Element("wu",
                            id=work.attrib["id"])

        if result:
            msg = "Could not remove environment variable {}".format(varname)
            ext_msg = msg + "Error code: {}".format(result)
            context.emsg(message)
            context.dmsg(ext_msg)
            res.attrib["status"] = "error"
            res.attrib["message"] = ext_msg
        else:
            res.attrib["status"] = "success"
        return res

    def generate_status(self):
        w_elt = etree.Element("Return")
        w_elt.attrib["method"] = "generate_status"
        w_elt.attrib["implemented"] = 0
        return w_elt
