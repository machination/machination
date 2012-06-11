#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker to set shortcuts in Windows."""

from lxml import etree
from machination import context
import win32com.client
import os
import shutil
import stat


class worker(object):
    logger = None
    shell = None
    windowstyles = {"normal": 1,
                    "max": 3,
                    "min": 7}

    s_props = {"name": "",
               "target": "",
               "windowStyleName": "",
               "window": 1,
               "iconFile": "",
               "iconNumber": "",
               "icon": "",
               "arguments": "",
               "description": "",
               "workingDir": "",
               "destination": "",
               "folderName": ""}

    def __init__(self, logger):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')
        shell = win32com.client.Dispatch("WScript.Shell")

    def do_work(self, work_list):
        "Process the work units and return their status."
        result = []
        for wu in work_list:
            operator = "__{}".format(wu.attrib["op"])
            res = getattr(self, operator)(wu)
            result.append(res)
        return result

    def __add(self, work):
        res = etree.element("wu",
                            id=work.attrib["id"])

        # Parse out shortcut properties from XML
        id = work[0].attrib["id"]
        for elem in work[0]:
            s_props[elem.tag] = elem.text

        if not s_props["iconFile"]:
            s_props["iconFile"] = s_props["target"]
        if not s_props["iconNumber"]:
            s_props["iconNumber"] = 0
        s_props["icon"] = ",".join(s_props["iconFile"],
                                   s_props["iconNumber"])
        s_props["name"] += ".lnk"
        if s_props["WindowStyleName"]:
            s_props["window"] = windowstyle[windowStyleName]

        if not target:
            msg = "Must provide target for shortcut " + id
            res.attrib["status"] = "error"
            res.attrib["message"] = msg
            context.emsg(msg)
            return res

        dest = shell.SpecialFolders(s_props["destination"])

        if s_props["folderName"]:
            dest = os.path.join(dest, s_props["folderName"])
            os.makedirs(dest)

        filename = os.path.join(dest, s_props["name"])
        link = shell.CreateShortcut(filename)
        link.TargetPath = s_props["target"]
        link.WindowStyle = s_props["window"]
        link.IconLocation = s_props["icon"]
        link.WorkingDirectory = s_props["workingDir"]
        link.Arguments = s_props["arguments"]
        link.Description = s_props["description"]
        link.Save()

        res.attrib["status"] = "success"
        return res

    def __datamod(self, work):
        d = self.__remove(work)
        if d.attrib["status"] == "error":
            return d
        return self.__add(work)

    def __deepmod(self, work):
        d = self.__remove(work)
        if d.attrib["status"] == "error":
            return d
        return self.__add(work)

    def __move(self, work):
        pass

    def __remove(self, work):
        res = etree.element("wu",
                            id=work.attrib["id"])

        id = work[0].attrib["id"]
        try:
            keepfolder = work[0].attrib["keepfolder"]
        except:
            keepfolder = true

        for elem in work[0]:
            s_props[elem.tag] = elem.text

        s_props["name"] += ".lnk"

        dest = shell.SpecialFolders(s_props["destination"])
        if s_props["folderName"]:
            dest = os.path.join(dest, s_props["folderName"])
        filename = os.path.join(dest, s_props["name"])

        os.remove(filename)

        res.attrib["status"] = success

        if not keepfolder:
            shutil.rmtree(dest,
                          ignore_errors=false,
                          onerror=self.handleRemoveReadonly)

        return res

    def handleRemoveReadOnly(self, func, path, exc):
        excvalue = exc[1]
        if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCESS:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.IRWXO)
            func(path)
        else:
            raise

    def generate_status(self):
        w_elt = etree.Element("Return")
        w_elt.attrib["method"] = "generate_status"
        w_elt.attrib["implemented"] = 0
        return w_elt
