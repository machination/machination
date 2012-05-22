#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker to add and remove Machination packages Windows."""


from lxml import etree
import machination
from machination import context
import os
import sys
from subprocess import call
import win32security
import win32ts
import win32process
import win32profile
import win32con


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
            f.write(etree.tostring(w_elt, pretty_print=True))

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
        back = self.__install(bundle_path,
                              work.find("pkginfo"),
                              work.attrib["interactive"])

        if back:
            context.emsg(back)
            res.attrib["status"] = "error"
            res.attrib["message"] = back
        else:
            res.attrib["status"] = "success"
        return res

    def __install(self, bundle, pkginfo, interactive):

        #Build command line

        if pkginfo.attrib["type"] == "msi":
            paramlist = {"REBOOT": "ReallySuppress",
                         "ALLUSERS": "1",
                         "ROOTDRIVE": "C:"}
            for arg in pkginfo.finditer("param"):
                # Check transform file exists
                if arg.attrib["name"] == "TRANSFORM":
                    tr_path = os.path.join(bundle, arg.text)
                    if not os.path.exists(tr_path):
                        return "Transform file not found."
                #Create list of msi options
                paramlist[arg.attrib["name"]] = arg.text

            msipath = os.path.join(bundle, pkginfo.find('startpoint').text)
            log = os.path.dirname(bundle) + os.path.basename(bundle) + ".log"
            opts = " ".join(["%s=%s" % (k, v) for k, v in paramlist])
            app = "msiexec"
            cmd = '/i {0} /qn /lvoicewarmup "{1}" {2}'.format(msipath,
                                                              log,
                                                              opts)

        elif pkginfo.attrib["type"] == "simple":
            app = sys.executable
            cmd = os.path.join(bundle, "install.py")

        # Execute command
        if not interactive:
            output = call([app, cmd])
        else:
            # Do stuff to make interactive/elevated installer work here
            output = self.__run_as_current_user(app, cmd)

        return output

    def __run_as_current_user(self, app, cmd):
        # Need to work out where elevate actually is.
        application = None
        elevate_path = "c:\\workspace\\elevate.py"
        commandline = " ".join([sys.executable,
                                elevate_path,
                                app,
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

    def generate_status(self):
        # Package status is stored in an external file
        w_elt = etree.parse(self.status_file)
        return w_elt
