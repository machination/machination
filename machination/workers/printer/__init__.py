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
    #TODO(Ali): Test woker for drivers that are not installed
    # check if /u stopmps on old drivers if given new ones
    # Test xerox first

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
            # We only expect 'printer' or 'model' work units
            if wu[0].tag not in ["printer", "model"]:
                msg = "Work unit of type: " + wu[0].tag
                msg += " not understood by packageman. Failing."
                self.log.emsg(msg)
                res = etree.Element("wu",
                                    id=wu.attrib["id"],
                                    status="error",
                                    message=msg)
                continue
            # No need to do anything for a model
            if wu[0].tag == 'model':
                res = etree.Element("wu",
                                    id=wu.attrib["id"])
                res.attrib["status"] = "success"
                result.append(res)
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

        # Start building a printui command
        printer = [os.path.join(
                   os.environ.get('SYSTEMROOT', os.path.join('C:', 'Windows')),
                   'system32', 'printui.exe')]
        # Use staged driver driver.
        printer.append('/u')
        # Construct human readable printer name ('base' name in
        # windows, hence /b).
        printer.extend(
            [
                '/b',
                self.descriptive_name(work[0])
                ]
            )
        # Queue name.
        printer.extend(['/n', work[0].get("id")])
        # 'Remote path' = port, url or path to print server queue
        printer.extend(['/r', work[0].xpath('remotePath')[0].text ])

        # Now we need model information. We'll need to get that from
        # context.desired_status. Outside of Machination a wrapper
        # script will need to supply a fake context.
        printer_model = work[0].xpath(
            'model/text()'
            )[0]
        xp = '/status/worker[@id="printer"]/model[@id="%s"]' % printer_model
        model_elt = context.desired_status.getroot().xpath(xp)[0]

        # Normally the driver name is the same as the model_elt id. In
        # exceptional circumstances it may be necessary to set
        # something different. In that case there should be a
        # driverName child of model.
        try:
            driverName = model_elt.xpath("driverName/text()")[0]
        except IndexError:
            driverName = model_elt.get("id")
        printer.extend(['/m',driverName])

        # Handle inf path differently depending on whether the driver
        # is built in or needed to be downloaded.
        bundle_elts = model_elt.xpath('machinationFetcherBundle')
        if bundle_elts:
            # We needed to download it. Fetcher should have done the
            # download already, we just have to point to the files.
            printer.extend(
                [
                    '/if', '/f',
                    os.path.join(context.cache_dir(),
                                 "bundles",
                                 bundle_elts[0].get("id"),
                                 model_elt.xpath('infFile/text()')[0])
                    ]
                )
        else:
            # No bundles: builtin driver.
            printer.extend(
                [
                    '/if', '/f',
                    os.path.join(
                        os.environ.get('windir'),'inf', 'ntdriver.inf'
                        )
                    ]
                )

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

        dname = self.descriptive_name(work[0])

        #do removal here
        printer = [os.path.join(
                   os.environ.get('SYSTEMROOT', os.path.join('C:', 'Windows')),
                   'system32', 'printui.exe'), '/dl', '/n']

        #use the wu id to get the name of the printer to remove
        printer.append(dname)

        print(printer)
        return_code = self.print_ui(printer)

        #check the return code from processAdd
        if return_code:
            res.attrib["status"] = "error"
        else:
            res.attrib["status"] = "success"

        return res

    def descriptive_name(self, wu):
        # Put the information from the XML into a dict for formatting
        # purposes.
        info = {
            'id':wu.get("id"),
            'location':wu.xpath('location')[0].text,
            'model':wu.xpath('model')[0].text,
            'remotePath':wu.xpath('remotePath')[0].text
            }
        return wu.xpath('descriptiveName')[0].text.format(**info)
