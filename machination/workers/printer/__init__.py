#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker to add printers in Windows."""

from lxml import etree
from machination import context
from machination import xmltools
from machination.xmltools import MRXpath
import win32com.client
import os
import shutil
import stat
import subprocess


class Worker(object):

    def __init__(self):
        self.log = context.logger
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')
        self.shell = win32com.client.Dispatch("WScript.Shell")

    def print_ui(self, printer):
        """Function to take in a list of args and tell
        subprocess to run them. Can be any list but first
         arg must be a valid program or command."""
        #using the list, printer tell subprocess.Popen
        #to run the comand printui.exe
        proc = subprocess.Popen(printer)
        return proc.wait()

    def do_work(self, work_list):
        "Process the work units and return their status."
        result = []
        for wu in work_list:
            if wu[0].tag != "printer":
                msg = "Work unit of type: " + wu[0].tag
                msg += " not understood by packageman. Failing."
                self.log.emsg(msg)
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

        #pass the work unit to a methord to get the
        #and return a list from the xml
        #take that and stick it into subprocess.popen

        cmdopts = {'basename': ['/u', '/b'],
                   'printer_name': ['/x', '/n'],
                   'net_addr': ['/r'],
                   'model': ['/m']}

        #inf can be built in so not in the defalt opts
        #get sysroot value from win rathere than explisetly calling it

        printer = [os.path.join(
                   os.environ.get('SYSTEMROOT', os.path.join('C:', 'Windows')),
                   'system32', 'printui.exe'), '/u']
        # pendent removal : #printer.append(work[0].get('id'))
        for key in cmdopts:
            printer.extend(cmdopts[key])
            printer.extend([work[0].xpath(key)[0].text])

        # Handle inf path differently depending on whether it is built
        # in or needed to be downloaded.
        bundle_elts = work[0].xpath('machinationFetcherBundle')
        if bundle_elts:
            # We needed to download it.
            printer.extend(
                [
                    '/if', '/f',
                    os.path.join(context.cache_dir(),
                                 "bundles",
                                 bundle_elts[0].get("id"),
                                 work[0].xpath('inf')[0].text)
                ]
            )
        else:
            if work[0].xpath('inf')[0].text:
                printer.extend(['/if', '/f', work[0].xpath('inf')[0].text])
            else:
                printer.extend(['/if', '/f',
                                os.path.join(
                                    os.environ.get('windir'),
                                    'inf', 'ntdriver.inf')])

        print(printer)
        #after parsing the xml go and add that printer
        return_code = self.print_ui(printer)

        #check the return code from processAdd
        if return_code:
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
        res = etree.Element("wu", wuId=work.attrib["id"])

        printer_id = MRXpath("/prof/wu[@id='printer'].getid()")

        #do removal here
        printer = [os.path.join(
                   os.environ.get('SYSTEMROOT', os.path.join('C:', 'Windows')),
                   'system32', 'printerui.exe'), '/dn']

        printer["name"] = printer_id
        printer.extend([work[0].xpath('basename')[0].text])
            #change above to only get the basename rather than listcomp
        #after parsing the xml go and remove that network printer

        return_code = self.print_ui(printer)

        #check the return code from processAdd
        if return_code:
            res.attrib["status"] = "error"
        else:
            res.attrib["status"] = "success"

        return res
