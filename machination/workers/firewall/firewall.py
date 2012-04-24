#!/usr/bin/python
# vim: set fileencoding=utf-8:

from lxml import etree
import wmi
import machination


class firewall(object):
    
    logger = None
    
    def __init__(self, logger):
        self.logger = logger

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
        res = etree.element("wu",
                            id=work.attrib["id"])

        #Do work here

        res.attrib["status"] = "success"
        return res

    def __modify(self, work):
        "Change existing environment variables"
        res = etree.element("wu",
                            id=work.attrib["id"])

        #Do work here

        res.attrib["status"] = "success"
        return res

    def __order(self, work):
        pass

    def __remove(self, work):
        "Remove unwanted variables"
        res = etree.element("wu",
                            id=work.attrib["id"])

        #Do work here

        res.attrib["status"] = "success"
        return res

    def generate_status(self):
        "Generate a status XML for this worker."
        return env_stat