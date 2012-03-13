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
from xml.etree import ElementTree
import wmi

def get_supported_platforms(config_file="./platform.xml"):
    """Open a list of supported platforms from disk and parse it into a
    list. Supported platforms exist in tags of the form:
    <platform id="foo" />
    
    Returns a list of platforms"""
    platform_list = []
    with open(config_file) as f:
        inputdata = ElementTree.parse(f)
    for avail_platform in inputdata.iter('platform'):
        platform_list.append(avail_platform.attrib["id"])
    return platform_list

def check_platform(supported_platforms=[]):
    """Get the current platform information and check it against a list of
    supported platforms, either provided as an argument or via
    get_supported_platforms().
    
    Returns the platform name, or exits if on an unsupported platform"""
    if not supported_platforms:
        supported_platforms = get_supported_platforms()

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
    """Returns a string containing the Windows distribution (XP, Vista, 7)"""
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
    return platform.releasei()

def machination_id(mach_id=None):
    """Parses the machination profile to extract the machination id.
    
    Returns the machination id"""
    if mach_id:
        return mach_id
        
    #FIXME: need better way to refer to machination profile
    mach_prof = "C:\program files\machination\profile\profile.xml"
    with open(mach_prof) as f:
        inputdata = ElementTree.parse(f)
    mach_id = inputdata.getroot().attrib["id"]
    return mach_id

def get_interactive_users(platform=None):
    """Gets the set of logged on users (currently Windows only) who are 
    logged in interactively.
    
    Returns a list of dictionaries containing domain, username,
    logon id, and session type."""
    logged_on = []
    if not platform:
        platform = check_platform(["Win7_64","WinXP_32"])
    if platform[:3] != "Win":
        # Do stuff for non-windows platforms
        return logged_on

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


