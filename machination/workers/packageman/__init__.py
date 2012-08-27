#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker to add and remove Machination packages in Windows."""

from lxml import etree
from machination import context
from machination import xmltools
from machination import platutils
import os
import sys
import subprocess
import wmi
import shutil
import glob

l = context.logger

class Worker(object):

    def __init__(self):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')

    def do_work(self, work_list):
        "Process the work units and return their status."
        result = []

        for wu in work_list:
            if wu.tag != "package":
                msg = "Work unit of type: " + wu.tag
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
        res = etree.Element("wu", id=work.attrib["id"])

        back = self._process(work, "install")

        if back:
            l.emsg(back)
            res.attrib["status"] = "error"
            res.attrib["message"] = "Installation failed: " + back
        else:
            res.attrib["status"] = "success"
        return res

    def _remove(self, work):
        res = etree.Element("wu", id=work.attrib["id"])

        back = self._process(work, "uninstall")

        if back:
            l.emsg(back)
            res.attrib["status"] = "error"
            res.attrib["message"] = back
        else:
            res.attrib["status"] = "success"
        return res

    def _datamod(self, work):
        d = self._remove(work)
        if d.attrib["status"] == "error":
            return d
        else:
            return self._add(work)

    def _deepmod(self, work):
        d = self._remove(work)
        if d.attrib["status"] == "error":
            return d
        else:
            return self._add(work)

    def _process(self, work, operation):
        # Prep necessary variables
        type = work.find("pkginfo").attrib["type"]
        bundle = work.find("machinationFetcherBundle").attrib["id"]
        bundle_path = os.path.join(context.cache_dir(),
                                   'bundles',
                                   bundle)
        if "interactive" in work.keys:
            inter = work.attrib["interactive"]
        else:
            inter = False

        # If it's interactive and not MSI, we need an uninstall check
        if inter and (type != "msi"):
            if not work.find("check"):
                err = "Interactive package without installation check: "
                err += bundle
                l.emsg(err)
                res.attrib["status"] = "error"
                res.attrib["message"] = err
                return res
            ins_check = [work.find("check").attrib["type"],
                         work.find("check").attrib["id"]]
        else:
            ins_check = None

        # MSIs have additional options in pkginfo
        if type == "msi":
            pkginfo = work.find("pkginfo")
        else:
            pkginfo = None

        op = "_{0}_{1}".format(operation, type)

        back = getattr(self, op)(bundle_path, pkginfo, check, inter)

        if not back:
            open(os.path.join(bundle_path,'.done'), 'a').close()

        return back

    def _install_msi(self, bundle, pkginfo, check, inter=False):
        paramlist = {"REBOOT": "ReallySuppress",
                     "ALLUSERS": "1",
                     "ROOTDRIVE": "C:"}

        # Build additional parameters
        for arg in pkginfo.finditer("param"):
            if arg.attrib["type"] == "uninstall":
                continue
            # If it's a transform, check that the file exists
            name = arg.attrib["name"].upper()
            val = arg.text
            if name == "TRANSFORM":
                tr_file = os.path.join(bundle, 'files', val)
                if not os.path.exists(tr_path):
                    return "Transform file not found: " + tr_path
            paramlist[name] = val

        msipath = os.path.join(bundle,
                               'files',
                               pkginfo.find('startpoint').text)

        log = os.path.dirname(bundle) + os.path.basename(bundle) + ".log"
        opts = " ".join(["%s=%s" % (k.upper(), v) for k, v in paramlist.items()])
        cmd = 'msiexec /i {0} /qn /lvoicewarmup "{1}" {2}'.format(msipath,
                                                          log,
                                                          opts)

        guid = platutils.win.get_installed_guid(msipath)
        with open(os.path.join(bundle, 'special', 'guid'), 'w') as f:
            f.write(guid)

        if inter:
            platutils.win.run_as_current_user(cmd)
            inscheck = self._check_reg(msi_guid)
            if inscheck:
                out = None
            else:
                out = "Installation failed."
        else:
            out = subprocess.call(cmd, stdout=subprocess.PIPE)

        return out

    def _install_simple(self, bundle, pkginfo, check, inter=False):
        # Simple apps are handled by calling an executable "install" file
        # from the package special directory

        try:
            cmd = glob.glob(os.path.join(bundle,
                                         'special',
                                         "install") + ".*")[0]
        except IndexError as e:
            return "Install script not found"

        if inter:
            platutils.win.run_as_current_user(cmd)
            operator = "_check_{0}".format(check[0])
            inscheck = getattr(self, operator)(check[1])
            if inscheck:
                out = None
            else:
                out = "Installation Failed."
        else:
            out = subprocess.call(cmd)

        return out

    def _uninstall_simple(self, bundle, pkginfo, check, inter=False):
        # Simple apps are handled by calling an executable "uninstall" file
        # from the package special directory

        try:
            cmd = glob.glob(os.path.join(bundle,
                                         'special',
                                         "uninstall") + ".*")[0]
        except IndexError as e:
            return "Unnstall script not found"

        if inter:
            platutils.win.run_as_current_user(cmd)
            operator = "_check_{0}".format(check[0])
            inscheck = getattr(self, operator)(check[1])
            if inscheck:
                out = "Uninstallation failed."
            else:
                out = None
        else:
            out = subprocess.call(cmd)

        return out

    def _uninstall_msi(self, bundle, pkginfo, check, inter=False):
        paramlist = {"REBOOT": "ReallySuppress",
                     "ALLUSERS": "1",
                     "ROOTDRIVE": "C:"}

        # Build additional parameters
        for arg in pkginfo.finditer("param"):
            if arg.attrib["type"] == "install":
                continue
            # If it's a transform, check that the file exists
            name = arg.attrib["name"].upper()
            val = arg.text
            if name == "TRANSFORM":
                tr_file = os.path.join(bundle, val)
                if not os.path.exists(tr_path):
                    return "Transform file not found: " + tr_path
            paramlist[name] = val

        with open (os.path.join(bundle, 'special', 'guid'), 'r') as f:
            guid = f.read()

        log = os.path.dirname(bundle) + os.path.basename(bundle) + ".log"
        opts = " ".join(["%s=%s" % (k.upper(), v) for k, v in paramlist.items()])
        cmd = 'msiexec /x {0} /qn /lvoicewarmup "{1}" {2}'.format(guid,
                                                          log,
                                                          opts)

        if inter:
            platutils.win.run_as_current_user(cmd)
            inscheck = self._check_reg(guid)
            if inscheck:
                out = "Uninstallation failed."
            else:
                out = None
        else:
            out = subprocess.call(cmd, stdout=subprocess.PIPE)

        return out

    def _check_file(self, filename):
        return os.path.exists(filename)

    def _check_reg(self, key):
        r = wmi.Registry()
        _HLKM = 2147483650
        reg_key = r"software\microsoft\windows\currentversion\uninstall"

        result, names = r.EnumKey(_HKLM, reg_key)

        if key in names:
            return True

        # 32 bit program so check that registry node
        reg_key = r"software\wow6432node\microsoft\windows\currentversion\uninstall"
        result, names = r.EnumKey(_HKLM, reg_key)

        if result:
            return False

        return key in names
