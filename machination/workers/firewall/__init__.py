#!/usr/bin/python
# vim: set fileencoding=utf-8:

from lxml import etree
from machination import context
from machination import xmltools
from pythoncom import com_error
import win32com.client

profiles = {1: "Domain", 2: "Private", 3: "Public"}
protocols = {1: "ICMP4", 6: "TCP", 17: "UDP", 58: "ICMP6"}
direction = {1: "In", 2: "Out"}
type = {0: "Block", 1: "Allow"}

class worker(object):
    
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

        # As firewall rules can have a few optional bits, read all
        # properties into a dictionary

        rule = {}
        rule["Name"] = work[0].id
        for property in work[0]:
            rule[property.tag] = property.text

        rule["Description"] = "mach_rule-" + rule["Description"]

        for val, action in self.type.iteritems():
            if action == rule["Action"]:
                rule["Action"] = val

        for val, protocol in self.protocols.iteritems():
            if protocol == rule["Protocol"].upper():
                rule["Protocol"] = val

        #Create a rule object
        ruleobj = win32com.client.gencache.EnsureDispatch("HNetCfg.FWRule",0)

        ruleobj.Name = rule["Name"]
        ruleobj.Description = rule["Description"]
        ruleobj.Protocol = rule["Protocol"]
        ruleobj.LocalPorts = rule["Port"]
        ruleobj.Action = rule["Action"]
        if "Application" in rule.keys():
            ruleobj.Applicationname = rule["Application"]
        if "Service" in rule.keys():
            ruleobj.Servicename = rule["Service"]
        ruleobj.Grouping = "@firewallapi.dll,-23255"
        ruleobj.Profiles = 1
        ruleobj.Enabled = True

        # Get a rules collection object
        rules = self.fwstat.Rules

        try:
            rules.Add(ruleobj)
        except com_error as error:
            hr,msg,exc,arg = error.args
            message = "Error adding rule: "
            message += win32api.FormatMessage(exc[5])
            emsg(message)
            res.attrib["message"] = message
            res.attrib["status"] = "error"
        else:
            res.attrib["status"] = "success"

        return res

    def __modify(self, work):
        "Change existing firewall rules variables"
        res = etree.element("wu",
                            id=work.attrib["id"])

        # The win7 firewall rule modification interface
        # is notoriously fragile. So let's not and say we did.

        d = self.__remove(work)
        if d.attrib["status"] == "error":
            return d
        a = self.__add(work)
        return a

    def __order(self, work):
        pass

    def __remove(self, work):
        "Remove unwanted firewall rules"
        res = etree.element("wu",
                            id=work.attrib["id"])

        rulename = work[0].attrib["id"]
        
        # Get a rules collection object
        rules = self.fwstat.Rules
        
        for rule in rules:
            if rule.Name = rulename:
                if rule.Description[:9] == "mach_rule"
                    control = True
        
        # We don't get any feedback ever so this will have to do.

        if control:
            rules.Remove(rulename)
            res.attrib["status"] = "success"
        else:
            msg = "Rule: " + rulename + " is not a Machination rule."
            res.attrib["message"] = msg
            res.attrib["status"] = "error"

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
            
            if not (rule.Description[:9] == "mach_rule"):
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