#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A machination module for worker utility functions.

Most of the job done by workers is the same, with only minor differences.
This library contains utility functions necessary to do that work."""

__author__ = "Stew Wilson"
__copyright__ = "Copyright 2012, Stew Wilson, University of Edinburgh"
__licence__ = "GPL"
__version__ = "trunk"
__maintainer__ = "stew.wilson"
__email__ = "stew.wilson@ed.ac.uk"
__status__ = "Development"

import sys
import os
import platform
import wmi
from lxml import etree


class MachUtils:
    "Class containing utility functions used throughout machination"

    def __init__(self, config_elt):
        self.config_data = config_elt
        for target in config_elt.xpath('/config/platform')[0]:
            if not isinstance(target.tag, str):
                continue
            self.platforms.append(target.attrib["id"])

    def machination_path(self):
        "Returns the Machination path"
        if platform.system()[:3] == "Win":
            try:
                r = wmi.Registry()
                # hDefKey should be _winreg.HKLM but that doesn't work on
                # win7_64
                result, path = r.GetStringValue(
                    hDefKey=2147483650,
                    sSubKeyName="Software\Machination",
                    sValueName="Path")
                if result:
                    # Registry read failed - use default path
                    # FIXME: Add syslog warning
                    path = 'c:\Program Files\Machination'
            except:
                # Something went wrong with the registry setup
                path = 'c:\program files\machination'
        else:
            #Try/Except block handles the exists/read race condition nicely
            try:
                with open("/etc/machination") as f:
                    path = f.readline()
            except IOError:
                #File doesn't exist
                path = '/opt/machination/'

        return path

    def get_platforms(self):
        "Returns a list of supported platforms"
        return self.platforms

    def check_platform(self):
        "Returns the platform name if supported or exits if platform is \
                not supported"
        if platform.system() == "Windows":
            if sys.maxsize > 2 ** 32:
                base_os = "Win" + platform.release() + "_64"
            else:
                base_os = "Win" + platform.release() + "_32"
        else:
            base_os = platform.system()

        for plat in self.platforms:
            if plat == base_os:
                return base_os
            else:
                sys.exit("Running on unknown platform: " + base_os)

    def win_distro(self):
        "Returns a string containing the Windows distribution"
        return "Win" + platform.release()

    def win_kernel(self):
        "Returns the kernel version of the Windows distribution"
        return platform.version()

    def linux_distro(self):
        "Returns the linux distribution, where available."""
        dirEntries = os.listdir('/etc')
        for entry in dirEntries:
            if entry[-8:] == "-release":
                return entry[:-8]
            else:
                sys.exit("No linux releases found (/etc/*-release)")

    def linux_kernel(self):
        """Returns the Linux kernel version"""
        return platform.release()

    def machination_id(self, serviceid):
        "Returns the machination id for the specified serviceid"

        try:
            xpath = "/config/services/service[@id={0}]".format(serviceid)
            mach_id = self.config_data.xpath(xpath)[0].attrib["mid"]
        except IndexError:
            # Xpath didn't return anything
            print("XPath error: Could not trace machination id")
            raise IndexError
        return mach_id

    def get_interactive_users(self, platform):
        "Gets the set of logged on users (currently Windows only)"

        logged_on = []
        if platform[:3] != "Win":
            # Do stuff for non-windows platforms
            return logged_on
        else:
            c = wmi.WMI()
            session_id = {}

            # Get sessions associated with processes
            for process in c.Win32_SessionProcess():
                logon_id = process.Antecedent.LogonId
                session_id[logon_id] = None

            # Get interactive sessions from active set
            for luser in c.Win32_LoggedOnUser():
                user_name = luser.Antecedent.Name
                user_dom = luser.Antecedent.Domain
                logon_id = luser.Dependent.LogonId
                if logon_id in session_id:
                    for sessions in c.Win32_LogonSession(LogonId=logon_id):
                        logon_type = sessions.LogonType
                        if logon_type == 2 or logon_type == 10:
                            user_dict = {
                                "Domain": user_dom,
                                "Name": user_name,
                                "SessionId": logon_id,
                                "LogonType": logon_type
                            }
                            logged_on.append(user_dict)

            return logged_on

    def is_interactive(self):
        """Simple truthiness boolean for when returning the full set of
        get_interactive_users() would be overkill"""
        return bool(self.get_interactive_users())

    def runner(self, cmd, **kwargs):
        "Runs an arbitrary external command in Windows via runner.exe"

        runner_loc = ["utils", "win32", "runner", "runner.exe"]
        runner = os.path.join(self.machination_path(),
                              os.sep.join(map(str, runner_loc)))
        command = '"' + runner + '"'
        if kwargs["hidden"]:
            command += " -h"
        if kwargs["time"]:
            command += " -t " + args["time"]
        command += " " + cmd

        return os.popen(command).readlines()

    def diskfree(self, disk="C"):
        "Checks free space on the specified disk in Windows"

        platform = self.check_platform()
        if platform[:3] != "Win":
            return 0

            c = wmi.WMI()

            for drive in c.Win32_LogicalDisk():
                if drive.name[0] == disk[0]:
                    return drive.freespace
                else:
                    print("Invalid disk specified: " + disk)
                raise IndexError
