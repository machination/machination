#!/usr/bin/python
# vim: set fileencoding=utf-8:

"A worker for setting Windows environment variables"

from lxml import etree
import wmi
from machination import context
import os

l = context.logger

class Worker(object):
    "Manipulates environment variables in Windows."

    #Define a shorthand constant for HKLM.
    _HKLM = 2147483650
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
            if wu[0].tag != "var":
                msg = "Work unit of type: " + wu[0].tag
                msg += " not understood by packageman. Failing."
                l.emsg(msg)
                res = etree.Element("wu",
                                    id=wu.attrib["id"],
                                    status="error",
                                    message=msg)
                continue
            operator = "_{}".format(wu.attrib["op"])
            res = getattr(self, operator)(wu)
            result.append(res)
        return result

    def _add(self, work):
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
        result = r.SetExpandedStringValue(hDefKey=self._HKLM,
                                  sSubKeyName=self.envloc,
                                  sValueName=varname,
                                  sValue=val)

        res = etree.Element("wu",
                            id=work.attrib["id"])
        if result:
            msg = "Could not set {0} to {1}".format(varname, val)
            ext_msg = msg + "Error code: {}".format(result)
            l.emsg(message)
            l.dmsg(ext_msg)
            res.attrib["status"] = "error"
            res.attrib["message"] = ext_msg
        else:
            res.attrib["status"] = "success"
        return res

    def _datamod(self, work):
        "Change existing environment variables"
        # Given that modifications to multi-vars are done in statuscompare
        # as <var> is the wu-tag, for registry entries, modify == add.
        return self._add(work)

    def _deepmod(self, work):
        "Change existing environment variables"
        # Given that modifications to multi-vars are done in statuscompare
        # as <var> is the wu-tag, for registry entries, modify == add.
        return self._add(work)

    def _remove(self, work):
        "Remove unwanted variables"
        # If we don't have notpres=1, it's an environment var that Machination
        # doesn't care about, so we just report a success
        if not work[1].attrib["notpres"]:
            res = etree.Element("wu", id=work.attrib["id"], status="success")
            return res

        # Since we actually care about it, get the variable name from the
        # XML passed as part of the wu
        varname = work[1].attrib["id"]
        result = r.DeleteValue(hDefKey=self._HKLM,
                               sSubKeyName=self.envloc,
                               sValueName=varname)
        res = etree.Element("wu",
                            id=work.attrib["id"])

        if result:
            msg = "Could not remove environment variable {}".format(varname)
            ext_msg = msg + "Error code: {}".format(result)
            l.emsg(message)
            l.dmsg(ext_msg)
            res.attrib["status"] = "error"
            res.attrib["message"] = ext_msg
        else:
            res.attrib["status"] = "success"
        return res
