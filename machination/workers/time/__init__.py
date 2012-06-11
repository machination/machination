#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker for Machination to modify NTP settings on Windows
   (enable/disable and set server)."""

from lxml import etree
from os import popen
from machination import context


class worker(object):
    sync_map = {"NTP": "MANUAL",
                "NT5DS": "DOMHIER",
                "AllSync": "ALL",
                "NoSync": "NO"}
    cmd = "w32tm"

    def __init__(self, logger):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')

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
            context.emsg("Could not set time server list: " + stream)
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
            context.emsg("Could not clear time server list: " + stream)
        return res

    def __deepmod(self, work):
        res = etree.element("wu", id=work.attrib["id"])
        # What are we changing?
        switch = work[1].tag.lower()
        if work[1].tag == "SyncFromFlags":
            opt = work[1].text
        elif work[1].tag == "ManualPeerList":
            peers = [peer.attrib["id"] for peer in work[1].iter("Peer")]
            opt = '"{0}"'.format(" ".join(peers))
        else:
            # This shouldn't happen
            msg = "{0} passed to modify.".format(switch)
            res.attrib["status"] = "error"
            res.attrib["message"] = msg
            wmsg(msg)
            return res
        command = "{0} /config /{1}:{2}".format(self.cmd, switch, opt)
        stream = popen(command)
        if stream[:-13] == "successfully.":
            res.attrib["status"] = "success"
        else:
            msg = "Could not modify {0}: {1}".format(work[1].tag, stream)
            res.attrib["status"] = "error"
            res.attrib["message"] = msg
            context.emsg(msg)
        return res

    def __datamod(self, work):
        return self.__deepmod(self, work)

    def __move(self, work):
        # Order makes no sense
        pass

    def generate_status(self):
        type = ""
        srvlist = []
        w_elt = etree.Element("Time")
        command = self.cmd + " /query /configuration"
        stream = popen(command)
        output = stream.read().splitlines()
        for line in output:
            if line[:4] == "Type":
                elt = etree.Element("SyncFromFlags")
                elt.text = self.sync_map[line[6:-8]]
            elif line[:10] == "NtpServer:":
                elt = etree.Element("ManualPeerList")
                servers = line[11:-8].split()
                for srv in servers:
                    peer = etree.Element("Peer")
                    peer.attrib["id"] = srv
                    elt.append(peer)
            w_elt.append(elt)
        return w_elt
