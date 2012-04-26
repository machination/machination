#!/usr/bin/python
# vim: set fileencoding=utf-8:

from lxml import etree
from machination import context
from machination import xmltools
import win32com.client

profiles = {1: "Domain", 2: "Private", 3: "Public"}
protocols = {1: "ICMP4", 6: "TCP", 17: "UDP", 58: "ICMP6"}
direction = {1: "In", 2: "Out"}
type = {0: "Block", 1: "Allow"}

class firewall(object):
    
    def __init__(self):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix = '/status')
        self.fwstat = win32com.client.gencache.EnsureDispatch("HNetCfg.FwPolicy2",0)

    def do_work(self, work_list):
        "Process the work units and return their status."
        result = []
        for wu in work_list:
            operator = "__{}".format(wu.attrib["op"])
            res = getattr(self, operator)(wu)
            result.append(res)
        return result

    def __add(self, work):
        "Add new firewall rules."
        res = etree.element("wu",
                            id=work.attrib["id"])

        #Do work here

        res.attrib["status"] = "success"
        return res

    def __modify(self, work):
        "Change existing firewall rules variables"
        res = etree.element("wu",
                            id=work.attrib["id"])

        #Do work here

        res.attrib["status"] = "success"
        return res

    def __order(self, work):
        pass

    def __remove(self, work):
        "Remove unwanted firewall rules"
        res = etree.element("wu",
                            id=work.attrib["id"])

        #Do work here

        res.attrib["status"] = "success"
        return res

    def generate_status(self):
        "Generate a status XML for this worker."
        w_elt = etree.Element("worker")
        w_elt.set("id", self.name)
        i = 0

        if not (self.fwstat.CurrentProfileTypes & 1):
            return w_elt

        rules = self.fwstat.Rules

        for rule in rules:
            if not rule.Profiles & 1:
                continue

            r_elt = etree.SubElement(w_elt, "Rule", id="rule-{}".format(i))

            etree.SubElement(r_elt, "Name").text = rule.Name
            etree.SubElement(r_elt, "Profiles").text = rule.Profiles
            etree.SubElement(r_elt, "Description").text = rule.Description
            etree.SubElement(r_elt, "AppName").text = rule.ApplicationName
            etree.SubElement(r_elt, "Protocol").text = protocols(rule.Protocol)
            if rule.Protocol in ["TCP", "UDP"]:
                etree.SubElement(r_elt, "LocalPort").text = rule.LocalPorts
                etree.SubElement(r_elt, "RemotePort").text = rule.RemotePorts
                etree.SubElement(r_elt, "LocalAddress").text = rule.LocalAddresses
                etree.SubElement(r_elt, "RemoteAddress").text = rule.RemoteAddresses
            else:
                etree.SubElement(r_elt, "ICMPTypeCode").text = rule.IcmpTypesAndCodes
            etree.SubElement(r_elt, "Direction").text = direction[rule.Direction]
            etree.SubElement(r_elt, "Enabled").text = rule.Enabled
            etree.SubElement(r_elt, "Action").text = type[rule.Action]
            i += 1

        return w_elt