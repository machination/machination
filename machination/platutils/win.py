#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A machination module for worker utility functions.

Most of the job done by workers is the same, with only minor differences.
This library contains utility functions necessary to do that work.

"""

__author__ = "Stew Wilson"
__copyright__ = "Copyright 2012, Stew Wilson, University of Edinburgh"
__licence__ = "GPL"
__version__ = "trunk"
__maintainer__ = "Stew Wilson"
__email__ = "Stew.Wilson@ed.ac.uk"
__status__ = "Development"

import sys
import os
import wmi


def get_interactive_users():
    "Gets the set of logged on users"

    logged_on = set()
    c = wmi.WMI()
    session_id = {process.Antecedent.LogonId for process in
                    c.Win32_SessionProcess()}

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

def is_interactive():
    """Simple truthiness boolean for when returning the full set of
    get_interactive_users() would be overkill"""
    return bool(get_interactive_users())

def runner(cmd, **kwargs):
    "Runs an arbitrary external command in Windows via runner.exe"

    runner_loc = ["utils", "win32", "runner", "runner.exe"]
    runner = os.path.join(machination_path(),
                          os.sep.join(map(str, runner_loc)))
    command = '"' + runner + '"'
    if kwargs["hidden"]:
        command += " -h"
    if kwargs["time"]:
        command += " -t " + args["time"]
    command += " " + cmd

    return os.popen(command).readlines()

def diskfree(disk="C"):
    "Checks free space on the specified disk in Windows"

    c = wmi.WMI()

    for drive in c.Win32_LogicalDisk():
        if drive.name[0] == disk[0]:
            return drive.freespace
    else:
        raise IndexError("Drive not found: {}".format(disk))
