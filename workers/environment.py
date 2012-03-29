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
    
    def __init__(self, logger):
        self.logger = logger

    def do_work(self, work_list):
        "Process the work units and return their status."
        for each wu in work_list:
            res = getattr(self, "__{}".format(wu.attrib["op"])(wu)
            out.append(res)
        return out
        
    def __add(self, work):
        pass

    def __modify(self, work):
        pass

    def __remove(self, work):
        "Remove unwanted values, when notpres is set to 1"
        
        # If we don't have notpres=1, it's an environment var that Machination
        # doesn't care about, so we just report a success
        if not work[1].attrib["notpres"]
            res = etree.element("wu", id=work.attrib["id"], status="success")
            return res
        
        r = wmi.registry()
        
        
    def generate_status(self):
        "Generate a status XML for this worker."
        # Get the environment variables
        env_dict = self.__parse_env()
        
        env_stat = etree.Element("environment")
        
        # Build status xml
        for key in env_dict:
            if key.upper() in multi_vars:
                line = self.__parse_multi(key, env_dict[key], multi_vars[key])
            else:
                line = etree.Element("var")
                line.attrib["id"] = key
                line.text = env_dict[key][1]
            env_stat.append(line)
        return env_stat

    def __parse_env(self):
        "Generate a dictionary of environment variables"
        env = {}
        r = wmi.Registry()

        [result, names, types] = r.EnumValues(hDefKey=_HKLM,sSubKeyName=envloc)
        if result:
            logger.emsg("Could not parse environment variables: {0}".format(result))

        for key, type in zip(names, types):
            method = "Get{0}Value".format(methods(type))
            result, value = getattr(r, method)(hDefKey=_HKLM,
                                               sSubKeyName=envloc,
                                               sValueName=key)
            if result:
                logger.emsg("Could not get value for {0}: {1}".format(key, result))
            else:
                env[key] = [methods(type), value]
        return env
        
    def __parse_multi(self, keyname, value, sep):
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

    def _setenv():
        pass
      