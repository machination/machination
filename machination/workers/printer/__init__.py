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
        #printer = {"printerui":(r"/in", "/u"), #check optins
#               "base_name":(r"/b","bname"),
#               "printer_name":(r"/x","/n","pname"),
#               "net_addr":(r"/r","addr"),
#               "inf":(r"/if","/f","inf"),
#               "driver":(r"/l","driv"),
#               "modal":(r"/m","modal")}

#remove before final commit(above is refrance only)

    def __init__(self):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')
        self.shell = win32com.client.Dispatch("WScript.Shell")

    def do_work(self, work_list):
        "Process the work units and return their status."
        result = []
        for wu in work_list:
            if wu[0].tag != "printer":
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
        #check if the worker is running in CMD mode(standalone installer)
        #if not then assume machination and add the printer
        #do printer additions in here
        #defins subprocsess.Popen and use it with printui.exe and the
        #options form printer{}

        #pass the work unit to a methord to get the and return a list from the xml
        #take that and stick it into subprocess.popen

        cmdopts = { 'basename': ['/b'],
                    'printer_name': ['/x', '/n'],
                    'net_addr': ['/r']
                    'inf': ['/if', '/f'],
                    'driver': ['/b', '/l'],
                    'modal': ['/m']}
        
        printer = ['/PATH/TO/printerui.exe','/in','/u']
        printer["name"] = work[0].id
        for property in work[0]:
            printer.extend(cmdopts[property.tag])
            printer.extend([x for x in cmdopts[property.tag]])
#            if property.tag == 'basename':
#                printer.extend(['/b',work[0].text])
#            elif property.tag == 'printer_name':
#                printer.extend(['/x','/n',work[0].text])
#            elif property.tag == 'net_addr':
#                printer.extend(['/r',work[0].text])
#            elif property.tag == 'inf':
#                printer.extend(['/if','/f',work[0].text])
#            elif property.tag == 'driver':
#                printer.extend(['/b','/l',work[0].text])
#            elif property.tag == 'modal':
#                printer.extend(['/m',work[0].text])

        processAdd(printer) #after parsing the xml go and add that printer

        if return_code == "1":  #check the return code from processAdd
            res.attrib["status"] = "error"
        else:
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

    def processAdd(self, printer):

        proc = Popen(printer) #using the list, printer tell subprocess.Popen to run the comand printui.exe
        return_code = proc.wait() #wait for it to finish
        return self.return_code
