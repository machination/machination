#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker to set shortcuts in Windows."""

from lxml import etree
from machination import context
import win32com.client
import os
import shutil
import stat

l = context.logger

class Worker(object):
        #printer options to printui, defalt construct
        printer = {"printerui":(r"/in", "/u"), #check optins
               "base_name":(r"/b","bname"),
               "printer_name":(r"/x","/n","pname"),
               "net_addr":(r"/r","addr"),
               "inf":(r"/if","/f","inf"),
               "driver":(r"/l","driv"),
               "modal":(r"/m","modal")}


    def __init__(self):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')
        self.shell = win32com.client.Dispatch("WScript.Shell")

    def do_work(self, work_list):
        "Process the work units and return their status."
        result = []
        for wu in work_list:
            if wu[0].tag != "shortcut":
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
        res = etree.Element("wu",
                            id=work.attrib["id"])

        #do printer additions in here
        #defins subprocsess.Popen and use it with printui.exe and the
        #options form printer{} 

        res.attrib["status"] = "success"
        return res

    def _datamod(self, work):
        d = self._remove(work)
        if d.attrib["status"] == "error":
            return d
        return self._add(work)

    def _deepmod(self, work):
        d = self._remove(work)
        if d.attrib["status"] == "error":
            return d
        return self._add(work)

    def _remove(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])

        id = work[0].attrib["id"]

        #do removal here

        return res
