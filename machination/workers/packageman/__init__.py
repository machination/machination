#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker to add and remove Machination packages Windows."""


from lxml import etree
from machination import context
import os
import sys
import subprocess
import win32security
import win32ts
import win32process
import win32profile
import win32con
import msilib
import wmi


class worker(object):

    def __init__(self):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix = '/status')

    def do_work(self, work_list):
        "Process the work units and return their status."
        result = []

        s_elt = etree.parse(self.status_file).getroot()

        for wu in work_list:
            operator = "__{}".format(wu.attrib["op"])
            res = getattr(self, operator)(wu, s_elt)
            result.append(res)
        return result

    def __add(self, work):
        res = etree.element("wu", id=work.attrib["id"])

        back = self.__install(work)

        if back:
            context.emsg(back)
            res.attrib["status"] = "error"
            res.attrib["message"] = "Installation failed: " + back
        else:
            res.attrib["status"] = "success"
        return res

    def __remove(self, work):
        res = etree.element("wu", id=work.attrib["id"])

        back = self.__uninstall(work)

        if back:
            context.emsg(back)
            res.attrib["status"] = "error"
            res.attrib["message"] = back
        else:
            res.attrib["status"] = "success"
        return res

    def __modify(self, work):
        return self.__add(work)

    def __order(self, work):
        pass

    def __install(self, work):
        return self.__process(work, "install")

    def __uninstall(self, work):
        return self.__process(work, "uninstall")

    def __process(self, work, operation):
        # Prep necessary variables
        type = work.find("pkginfo").attrib["type"]
        if (type == "msi") and (operation == "uninstall"):
            # Get the guid from the installation file


        bundle = work.find("bundle").attrib["id"]
        bundle_path = os.path.join(context.cache_dir(),
                                   "files",
                                   bundle)
        if "interactive" in work.keys:
            inter = work.attrib["interactive"]
        else:
            inter = False

        # If it's interactive and not MSI, we need an uninstall check
        if inter and (type not "msi"):
            if not work.find("check"):
                err = "Interactive package without installation check: "
                err += bundle
                context.emsg(err)
                res.attrib["status"] = "error"
                res.attrib["message"] = err
                return res
            ins_check = (work.find("check").attrib["type"],
                         work.find("check").attrib["id"])
        else:
            ins_check = None

        # MSIs have additional options in pkginfo
        if type = "msi":
            pkginfo = work.find("pkginfo")
        else:
            pkginfo = None

        op = "__{0}_{1}".format(operation, type)

        back = getattr(self, op)(bundle_path, pkginfo, check, inter)

    def __install_msi(self, bundle, pkginfo, check, inter=False):
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
            if name == "TRANSFORM"
                tr_file = os.path.join(bundle, val)
                if not os.path.exists(tr_path):
                    return "Transform file not found: " + tr_path
            paramlist[name] = val

        msipath = os.path.join(bundle, pkginfo.find('startpoint').text)

        log = os.path.dirname(bundle) + os.path.basename(bundle) + ".log"
        opts = " ".join(["%s=%s" % (k.uppercase, v) for k, v in paramlist])
        cmd = 'msiexec /i {0} /qn /lvoicewarmup "{1}" {2}'.format(msipath,
                                                          log,
                                                          opts)

        if inter:
            self.__run_as_current_user(cmd)
            guid = self.__get_installed_guid(msipath)
            out = self.__check_reg(msi_guid, True)
            if out:
                out = "Installation failed."
        else:
            out = subprocess.call(cmd, stdout=subprocess.PIPE)

        return out

    def __install_simple(self, bundle, pkginfo, check, inter=False):
        # Simple apps are handled by calling install.py from the bundle
        # directory
        install_file = os.path.join(bundle, "install.py")

        if not os.path.exists(install_file):
            return "Install.py not found: " + install_file

        cmd = " ".join([sys.executable, install_file])

        if inter:
            self.__run_as_current_user(cmd)
            operator = "__check_{0}".format(check[0])
            out = getattr(self, operator)(check[1], True)
            if out:
                out = "Installation failed."
        else:
            out = subprocess.call(cmd)

        return out

    def __uninstall_simple(self, bundle, pkginfo, check, inter=False):
        # Simple apps are handled by calling install.py from the bundle
        # directory
        install_file = os.path.join(bundle, "uninstall.py")

        if not os.path.exists(install_file):
            return "Uninstall.py not found: " + install_file

        cmd = " ".join([sys.executable, install_file])

        if inter:
            self.__run_as_current_user(cmd)
            operator = "__check_{0}".format(check[0])
            out = getattr(self, operator)(check[1])
            if out:
                out = "Uninstallation failed."
        else:
            out = subprocess.call(cmd)

        return out

    def __uninstall_msi(self, bundle, pkginfo, check, inter=False):
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
            if name == "TRANSFORM"
                tr_file = os.path.join(bundle, val)
                if not os.path.exists(tr_path):
                    return "Transform file not found: " + tr_path
            paramlist[name] = val

        msipath = os.path.join(bundle, pkginfo.find('startpoint').text)
        guid = self.__get_installed_guid(msipath)

        log = os.path.dirname(bundle) + os.path.basename(bundle) + ".log"
        opts = " ".join(["%s=%s" % (k.uppercase, v) for k, v in paramlist])
        cmd = 'msiexec /x {0} /qn /lvoicewarmup "{1}" {2}'.format(guid,
                                                          log,
                                                          opts)

        if inter:
            self.__run_as_current_user(cmd)
            out = self.__check_reg(guid)
            if out:
                out = "Uninstallation failed."
        else:
            out = subprocess.call(cmd, stdout=subprocess.PIPE)

        return out

    def __get_installed_guid(self, msi):
        # Open msi database read only
        db = msilib.OpenDatabase(msi, 0)
        v = "SELECT Value FROM Property WHERE Property='ProductCode'"
        view = db.OpenView(v)
        view.Execute(None)
        result = view.Fetch()
        return result.GetString(1)

    def __check_file(self, filename, invert=False):
        back = os.path.exists(filename)
        if invert:
            back = not back
        return back

    def __check_reg(self, key, invert=False):
        r = wmi.Registry()
        __HLKM = 2147483650
        uloc = "software\microsoft\windows\currentversion\uninstall"

        result, names = r.EnumKey(HKLM, uloc)

        if key in names:
            back = True
        else:
            uloc = "software\wow6432node\microsoft\windows\currentversion\uninstall"
            result, names = r.EnumKey(HKLM, uloc2)

            if result:
                # Reg key not found--running on 32bit system
                back = False

            if key in names:
                back = True
            else
                back = False

        if invert:
            return not back
        else
            return back

    def __run_as_current_user(self, cmd):
        # Need to work out where elevate actually is. Assume for now
        # that it's in bin_dir
        application = None
        elevate_path = os.path.join(context.bin_dir(), "elevate.py")
        commandline = " ".join([sys.executable,
                                elevate_path,
                                "'"+cmd+"'"])
        workingDir = None

        # Find the active session
        sessionid = win32ts.WTSGetActiveConsoleSessionId()

        # Get the user token from that session
        token = win32ts.WTSQueryUserToken(sessionid)

        # We might want to load user's environment here?
        # (win32profile.CreateEnvironmentBlock etc)


        win32security.ImpersonateLoggedOnUser(token)

        # Setup appropriate desktop and window stuff
        si = win32process.STARTUPINFO()
        si.lpDesktop = u'Winsta0\\default'

        #Launch the user script

        # This doesn't give us any means of trapping output
        # CreateProcessAsUser returns the results of *creating* the process
        # rather than the results of the created process.
        win32process.CreateProcessAsUser(
            token,
            application,
            commandline,
            None,
            None,
            False,
            win32con.NORMAL_PRIORITY_CLASS | win32con.CREATE_NEW_CONSOLE,
            env,
            workingDir,
            si
            )

    def generate_status(self):
        # Update can keep track of packages.
        w_elt = etree.Element("Return")
        w_elt.attrib["method"] = "generate_status"
        w_elt.attrib["implemented"] = 0
        return w_elt
