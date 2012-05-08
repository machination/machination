#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker to set shortcuts in Windows."""

from lxml import etree
import machination
import win32com.client
import os
import shutil
import stat


class shortcut(object):
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
        self.logger = logger
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

        s_props["iconFile"] = s_props["target"] if (not s_props["iconFile"])
        s_props["iconNumber"] = "0" if not s_props["iconFile"]
        s_props["icon"] = ",".join(s_props["iconFile"],
                                   s_props["iconNumber"])
        s_props["name"] += ".lnk"
        if s_props["WindowStyleName"]:
            s_props["window"] = windowstyle[windowStyleName]

        if not target:
            msg = "Must provide shortcut for target"
            res.attrib["status"] = "error"
            res.attrib["message"] = msg
            logger.emsg(msg)

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

    def __modify(self, work):
        d = self.__remove(work)
        if d.attrib["status"] == "error":
            return d
        a = self.__add(work)
        return a

    def __order(self, work):
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
        ret = etree.Element("Return")
        ret.attrib["method"] = "generate_status"
        ret.attrib["implemented"] = 0
        return ret
