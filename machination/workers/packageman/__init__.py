#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker to add and remove Machination packages Windows."""


from lxml import etree
import machination
from machination import context
import os


class worker(object):

    def __init__(self):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix = '/status')
        self.status_file = os.path.join(context.status_dir(),
                                        "packageman",
                                        status.xml)
        # Create status file if it doesn't exist
        f = open(self.status_file, "r+")
        a = f.read()
        if a == "":
            w_elt = etree.Element("worker", id=self.name)
            f.write(etree.tostring(w_elt, pretty_print=True)
        f.close()

    def do_work(self, work_list):
        "Process the work units and return their status."
        result = []

        s_elt = etree.parse(self.status_file).getroot()

        for wu in work_list:
            operator = "__{}".format(wu.attrib["op"])
            res = getattr(self, operator)(wu)
            result.append(res)
            #TODO: Implement MSI product code trapping
            if res.attrib["status"] == "success":
                s_elt.append(wu[0])

        with open(self.status_file, "w") as f:
            f.write(etree.tostring(s_elt, pretty_print=True))

        return result

    def __add(self, work):
        res = etree.element("wu",
                            id=work.attrib["id"])
        bundle = work.find("bundle").attrib["id"]
        bundle_path = os.path.join(context.cache_dir(),
                                   "files",
                                   bundle)
        if work.attrib["interactive"] == 1:
            back = self.__install_inter(bundle_path, work.find("pkginfo")
        else:
            back = self.__install_std(bundle_path, work.find("pkginfo")

            #startpoint =
            #param dict
            #upgrade
            #func = "__install_msi" + inter
            #back = getattr(self, func)(bundle, startpoint, param, upgrade)

        res.attrib["status"] = "success"
        return res

    def __install_std(self, bundle, pkginfo)
        if pkginfo.attrib["type"] == "msi"
            paramlist = {"REBOOT": "ReallySuppress",
                         "ALLUSERS": "1",
                         "ROOTDRIVE": "C:"}
            for arg in pkginfo.finditer("param"):
                paramlist[arg.attrib["name"]] = arg.text

            #TODO: Transform file checking.

            msipath = os.path.join(bundle, pkginfo.find('startpoint').text)
            cmd = 'msiexec /i {} /qn /lvoicewarmup "..\\$pid.log"'.format


    def __remove(self, work):
        res = etree.element("wu",
                            id=work.attrib["id"])

        res.attrib["status"] = "success"
        return res

    def __modify(self, work):
        res = etree.element("wu",
                            id=work.attrib["id"])

        res.attrib["status"] = "success"
        return res

    def __order(self, work):
        pass

    def __install_simple(self, bundle, inter):
        if inter


    def generate_status(self):
        # Package status is stored in an external file
        w_elt = etree.parse(self.status_file)
        return w_elt
