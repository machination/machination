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

        cmdopts = {'printerName': ['/x', '/n', work[0].get("id") ],
                   'remotePath': ['/r', work[0].xpath('remotePath')[0].text ],
                   'model': ['/m', work[0].xpath('model')[0].text ]}

        printer = [os.path.join(
                   os.environ.get('SYSTEMROOT', os.path.join('C:', 'Windows')),
                   'system32', 'printui.exe'), '/u', '/b']

        printer_description = {'id':work[0].get("id"),
                               'location':work[0].xpath('location')[0].text,
                               'model':work[0].xpath('model')[0].text,
                               'remotePath':work[0].xpath('remotePath')[0].text}

        printer.append(work[0].xpath('descriptiveName')[0].text.format(**printer_info))


        for key in cmdopts:
            printer.extend(cmdopts[key])

        print(printer)
        # Need a context module to get desired_status from. Outside of Machination a wrapper script will have to construct this.
        xp = '/status/worker[@id="printer"]/model[@id="%s"]' % (printer_info.get("model"))
        model_elt = context.desired_status.getroot().xpath(xp)[0]

        #get context.desierd_status(this is a status xml file).getroot().xpath(
        #                                               /worker=printer/modal=foo)
        #this will get the modal driver bundal and parse it for the values it neads

        # Handle inf path differently depending on whether it is built
        # in or needed to be downloaded.
        bundle_elts = model_elt.xpath('machinationFetcherBundle')
        if bundle_elts:
            # We needed to download it.
            printer.extend(
                [
                    '/if', '/f',
                    os.path.join(context.cache_dir(),
                                 "bundles",
                                 bundle_elts[0].get("id"),
                                 model_elt.xpath('infFile')[0].text)
                ]
            )
        elif model_elt('infFolder'):
             if model_elt.xpath('infFile')[0].text:
                printer.extend(['/if', '/f', model_elt.xpath('infFile')[0].text])
                printer.extend(['/l', model_elt('infFolder')[0].text])
        else:
            if model_elt.xpath('infFile')[0].text:
                printer.extend(['/if', '/f', model_elt.xpath('infFile')[0].text])
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
        res = etree.Element("wu", id=work.attrib["id"])

        printer_id = MRXpath("/prof/wu[@id='printer'].getid()")

        #do removal here
        printer = [os.path.join(
                   os.environ.get('SYSTEMROOT', os.path.join('C:', 'Windows')),
                   'system32', 'printui.exe'), '/dl', '/n']

        #use the wu id to get the name of the printer to remove
        printer.extend([work[0].xpath('basename')[0].text])

        #after parsing the xml go and remove that network printer
        print(printer)
        return_code = self.print_ui(printer)

        #check the return code from processAdd
        if return_code:
            res.attrib["status"] = "error"
        else:
            res.attrib["status"] = "success"

        return res
