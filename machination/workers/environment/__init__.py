#!/usr/bin/python
# vim: set fileencoding=utf-8:

"A worker for setting Windows environment variables"

from lxml import etree
import wmi
from machination import context
import os


class worker(object):
    "Manipulates environment variables in Windows."

    r = None

    #Define a shorthand constant for HKLM.
    __HLKM = 2147483650
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
        result = r.SetExpandedStringValue(hDefKey=__HKLM,
                                  sSubKeyName=envloc,
                                  sValueName=varname,
                                  sValue=val)

        res = etree.element("wu",
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
        result = r.DeleteValue(hDefKey=_HKCU,
                               sSubKeyName=envloc,
                               sValueName=varname)
        res = etree.element("wu",
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
        "Generate a status XML for this worker."
        # Get the environment variables
        env_dict = self.__parse_env()
        w_elt = etree.Element("environment")

        # Build status xml
        for key in env_dict:
            if key.upper() in multi_vars:
                line = self.__parse_multi(key, env_dict[key], multi_vars[key])
            else:
                line = etree.Element("var")
                line.attrib["id"] = key
                line.text = env_dict[key][1]
            w_elt.append(line)
        return w_elt

    def __parse_env(self):
        "Generate a dictionary of environment variables"
        env = {}

        [result, names, types] = r.EnumValues(hDefKey=__HKLM,
                                              sSubKeyName=envloc)
        if result:
            context.emsg("Could not parse environment vars: {0}".format(result))

        for key, type in zip(names, types):
            method = "Get{0}Value".format(methods(type))
            result, value = getattr(r, method)(hDefKey=__HKLM,
                                               sSubKeyName=envloc,
                                               sValueName=key)
            if result:
                context.emsg("Could not get {0} value: {1}".format(key, result))
            else:
                env[key] = [methods(type), value]
        return env

    def __parse_multi(self, keyname, value, sep):
        "Creates the XML output for multi-value environment variables."
        # Each id needs to be unique, so use count as an incrementing index
        count = 0

        # Set up the <var> element
        out = etree.Element("var",
                            id=keyname,
                            type="multiple",
                            separator=sep)

        # Split value on sep and transform into <items>
        for val in value[1].split(sep):
            line = etree.Element("item", id=count)
            line.text = val
            out.append(line)
            count += 1
        return out
