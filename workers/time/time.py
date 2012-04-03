#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker for Machination functions not deemed important enough to have
their own worker.

Currently only handles NTP (enable/disable and ser server)."""

from lxml import etree
from os import popen
import machination

class tweaks(object):
    logger = None
    #Define a shorthand constant for HKLM.
    sync_map{"NTP": "MANUAL",
             "NT5DS": "DOMHIER",
             "AllSync": "ALL"
             "NoSync": "NO"}
    cmd = "w32tm"
    
    def __init__(self, logger):
        self.logger = logger

    def do_work(self, work_list):
        "Process the work units and return their status."
        result = []
        for wu in work_list:
            operator = "__{}".format(wu.attrib["op"])
            res = getattr(self, operator)(wu)
            result.append(res)
        command = "net stop w32time && net start w32time"
        stream = popen(command)
        return result
    
    def __add(self, work):
        # Add can only be called on ManualPeerList
        res = etree.element("wu", id=work.attrib["id"])
        peers = [peer.attrib["id"] for peer in work[1].iter("Peer")]
        flat = " ".join(peers)
        command = '{0} /config /manualpeerlist:"{1}"'.format(self.cmd, flat)
        stream = popen(command)
        if stream[:-13] == "successfully.":
            res.attrib["status"] = "success"
        else:
            res.attrib["status"] = "error"
            res.attrib["message"] = stream
            logger.wmsg("Could not set time server list: " + stream)
        return res

    def __remove(self, work):
        # Remove can only be called on ManualPeerList
        res = etree.element("wu", id=work.attrib["id"])
        command = self.cmd + ' /config /manualpeerlist:""'
        stream = popen(command)
        if stream[:-13] == "successfully.":
            res.attrib["status"] = "success"
        else:
            res.attrib["status"] = "error"
            res.attrib["message"] = stream
            logger.wmsg("Could not clear time server list: " + stream)
        return res

    def __modify(self, work):
        res = etree.element("wu", id=work.attrib["id"])
        # What are we changing?
        switch = work[1].tag.lower()
        if work[1].tag == "SyncFromFlags":
            opt = work[1].text
        elif work[1].tag == "ManualPeerList:
            peers = [peer.attrib["id"] for peer in work[1].iter("Peer")]
            opt = '"{0}"'.format(" ".join(peers))
        else:
            # This shouldn't happen
            msg = "{0} passed to modify.".format(switch)
            res.attrib["status"] = "error"
            res.attrib["message"] = msg
            logger.wmsg(msg)
            return res
        command = "{0} /config /{1}:{2}".format(self.cmd, switch, opt)
        stream = popen(command)
        if stream[:-13] == "successfully.":
            res.attrib["status"] = "success"
        else:
            msg = "Could not modify {0}: {1}".format(work[1].tag, stream)
            res.attrib["status"] = "error"
            res.attrib["message"] = msg
            logger.wmsg(msg)
        return res

    def __order(self, work)
        # Order makes no sense
        pass

    def generate_status(self):
        type = ""
        srvlist = []
        status_elt = etree.Element("Time")
        command = self.cmd + " /query /configuration"
        stream = popen(command)
        output = stream.read().splitlines()
        for line in output:
            if line[:4] == "Type":
                elt = etree.Element("SyncFromFlags")
                elt.text = self.sync_map{line[6:-8])
            elif line[:10] == "NtpServer:":
                elt = etree.Element("ManualPeerList")
                servers = line[11:-8].split()
                for srv in servers:
                    peer = etree.Element("Peer")
                    peer.attrib["id"] = srv
                    elt.append(peer)
            status_elt.append(elt)
        return status_elt