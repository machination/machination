#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker to add printers in Windows."""

from lxml import etree
from machination import context
import win32com.client
import os
import shutil
import stat

l = context.logger

class Worker(object):

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
                    'net_addr': ['/r'],
#inf can be built in so not in the defalt opts
#                    'inf': ['/if', '/f'],
                    'driver': ['/b', '/l'],
                    'model': ['/m']}

        printer = ['/PATH/TO/printerui.exe','/in','/u']
        printer["name"] = work[0].get('id')
        for property in work[0]:
            printer.extend(cmdopts[property.tag])
            printer.extend([x for x in cmdopts[property.tag]])

        # Handle inf path differently depending on whether it is built
        # in or needed to be downloaded.
        bundle_elts = work[0].xpath('machinationFetcherBundle')
        if bundle_elts:
            # We needed to download it.
            printer.extend(
                [
                    '/if','/f',
                    os.path.join(context.cache_dir(),
                                 "bundles",
                                 bundle_elts[0].get("id"),
                                 work[0].xpath('inf')[0].text)
                ]
            )
        else:
            printer.extend(['/if', '/f', work[0].xpath('inf')[0].text])

        processAdd(printer) #after parsing the xml go and add that printer

        if return_code:  #check the return code from processAdd
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
        return proc.wait() #wait for it to finish
