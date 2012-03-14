#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A machination module for worker utility functions.

Most of the job done by workers is the same, with only minor differences. This library contains utility functions necessary to do that work.

"""

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
import _winreg
from lxml import etree

def machination_path:
    """Returns the Machination path, which can be stored in a few places:
        Windows has it in HKLM\Software\Machination
        Linux has it in /etc/machination
        
    If these entries don't exist, fall back to reasonable defaults.
    
    Returns the machination path."""
    if platform.system()[:3] = "Win":
        try:
            r = wmi.Registry()
            result, path = r.GetStringValue(
                #hDefKey=_winreg.HKEY_LOCAL_MACHINE,
                # If only. _winreg.HKEY_LOCAL_MACHINE is b0rked on Win7_64
                # and possibly others.
                hDefKey=2147483650
                sSubKeyName = "Software\Machination"
                sValueName = "Path"
            )
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

def get_supported_platforms(config_file=None):
    """Open a list of supported platforms from disk and parse it into a
    list. Supported platforms exist in tags of the form:
    <platform id="foo" />
    
    Returns a list of platforms"""
    
    if config_file=None
        config_file = machination_path() + '/config/platforms.xml'
    platform_list = []
    with open(config_file) as f:
        inputdata = etree.parse(f)
    for avail_platform in inputdata.iter('platform'):
        platform_list.append(avail_platform.attrib["id"])
    return platform_list

def check_platform(supported_platforms=[]):
    """Get the current platform information and check it against a list of
    supported platforms, either provided as an argument or via
    get_supported_platforms().
    
    Returns the platform name, or exits if on an unsupported platform"""

    if not supported_platforms:
        supported_platforms =
        get_supported_platforms('../../tests/example_platforms.xml')

    if platform.system() = "Windows":
        if sys.maxsize > 2**32:
            base_os = "Win"+platform.release()+"_64"
        else
            base_os = "Win"+platform.release()+"_32"
    else
        base_os = platform.system()
    
    for plat in supported_platforms:
        if plat = base_os:
            return base_os
    else
        sys.exit("Running on unknown platform: " + base_os)

def win_distro:
    """Returns a string containing the Windows distribution 
    
    Could be WinXP, WinVista, or Win7"""

    return "Win" + platform.release()

def win_kernel:
    """Returns the kernel version of the Windows distribution"""

    return platform.version()

def linux_distro:
    """Returns the distribution name of a linux machine, where available."""

    dirEntries = os.listdir(/etc)
    for entry in dirEntries
        if entry[-8:] = "-release":
            return entry[:-8]
    else
        sys.exit("No linux releases found (/etc/*-release)")
        
def linux_kernel:
    """Returns the Linux kernel version"""

    return platform.release()

def machination_id(mach_id=None):
    """Parses the machination profile to extract the machination id.
    
    Returns the machination id"""

    if mach_id:
        return mach_id
        
    #FIXME: need better way to refer to machination profile
    mach_prof = machination_path() + '/profile/profile.xml'
    with open(mach_prof) as f:
        inputdata = etree.parse(f)
    mach_id = inputdata.getroot().attrib["id"]
    return mach_id

def get_interactive_users(platform=None):
    """Gets the set of logged on users (currently Windows only) who are 
    logged in interactively.
    
    Returns a list of dictionaries containing domain, username,
    logon id, and session type."""

    logged_on = []
    if not platform:
        platform = check_platform()
    if platform[:3] != "Win":
        # Do stuff for non-windows platforms
        return logged_on
    else:
        c = wmi.WMI()
    
        session_id={}
        
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
                    if logon_type == 2|| logon_type == 10:
                        user_dict = {
                            "Domain": user_dom,
                            "Name": user_name,
                            "SessionId": logon_id,
                            "LogonType": logon_type
                        }
                        logged_on.append(user_dict)

        return logged_on

def is_interactive:
    """Simple truthiness boolean for when returning the full set of
    get_interactive_users() would be overkill"""

    if get_interactive_users():
        return True
    else:
        return False

def runner(cmd, args={}):
    """Runs an arbitrary external command in Windows via runner.exe.
    Takes two arguments:
        1. The command to run
        2. An optional dictionary of arguments

    Returns the results of the command."""
    
    runner = machination_path() + '/utils/win32/runner/runner.exe'
    command = '"' + runner '"'
    if args["hidden"]:
        command += " -h"
    if args["time"]:
        command += " -t " + args["time"]
    command += " " + cmd
    
    return os.popen(command).readlines()

def diskfree(disk="C"):
    """Checks free space on the specified disk
    Only works on Windows.

    Returns number of bytes free on the disk"""
