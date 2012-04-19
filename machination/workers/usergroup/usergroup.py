#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker to create/modify user accounts and groups in Windows."""


from lxml import etree
import machination
import win32netcon
import win32com.client
import win32net
import wmi
from platform import uname


class usergroup(object):
    logger = None

    def __init__(self, logger):
        u = {}

        sp_users = ("Administrator",
                    "ASPNET",
                    "Guest",
                    "HelpAssistant",
                    "SUPPORT_388945a0")

        sp_groups = ("Administrators",
                     "Backup Operators",
                     "Guests",
                     "Network Configuration Operators",
                     "Power Users",
                     "Remote Desktop Users",
                     "Replicator",
                     "Users",
                     "HelpServicesGroup")

        self.logger = logger

    def do_work(self, work_list):
        "Process the work units and return their status."
        result = []
        for wu in work_list:
            operator = "__{}".format(wu.attrib["op"])
            res = getattr(self, operator)(wu)
            result.append(res)
        return result

    def __add_user(self, username, password, expire, description=None):
        u = {"name": username,
             "password": password,
             "comment": description,
             "flags": win32netcon.UF_NORMAL_ACCOUNT | win32netcon.UFSCRIPT,
             "priv": win32netcon.UF_PRIV_USER
            }

        if expire == 0:
            u["flags"] |= win32netcon.UF_DONT_EXPIRE_PASSWD

        try:
            win32net.NetUserAdd(None, 1, u)
            return None
        except win32net.error as error:
            errno, errctx, errmsg = error.args
            return errmsg

    def __mod_user(self, user, kw):
        info = win32net.NetUserGetInfo(None, user, 3)
        for k in kw:
            # Password expiration is a bitwise flag
            if k == "password_can_expire":
                info["flags"] |= win32netcon.UF_DONT_EXPIRE_PASSWD
            # Don't change the user's password -- else for every change
            # we'd reset the user's password.
            elif k == "initialPassword":
                continue
            elif k in info.keys():
                info[k] = kw[k]
            else:
                return "Can't change userinfo {}".format(k)
        try:
            win32net.NetUserSetInfo(None, user, 3, info)
            return None
        except win32net.error as error:
            errno, errctx, errmsg = error.args
            return errmsg

    def __del_user(self, username):
        # Don't ever delete special user accounts
        if username in sp_users:
            return None
        try:
            win32net.NetUserDel(None, username)
            return None
        except win32net.error as error:
            errno, errctx, errmsg = error.args
            return errmsg

    def __add_group(self, name):
        g_info = {"name": name}

        if name in sp_groups:
            return "Cannot add a special group"

        try:
            win32net.NetLocalGroupAdd(None, 1, g_info)
            return None
        except win32net.error as error:
            errno, errctx, errmsg = error.args
            return errmsg

    def __del_group(self, name):
        if name in sp_groups:
            return None
        try:
            win32net.NetLocalGroupDel(None, name)
            return None
        except win32net.error as error:
            errno, errctx, errmsg = error.args
            return errmsg

    def __add_user_to_group(self, user, group, domain=None):
        if domain:
            userstring = u"\\".join([domain.upper(), user])
        else:
            userstring = user

        ug_info = {"domainandname": userstring}

        try:
            win32net.NetLocalGroupAddMembers(None, group, 3,[ug_info])
            return None
        except win32net.error as error:
            errno, errctx, errmsg = error.args
            return errmsg

    def __del_user_from_group(self, user, group, domain=None):
        if domain:
            userstring = u"\\".join([domain.upper(), user])
        else:
            userstring = user

        ug_info = {"domainandname": userstring}
        try:
            win32net.NetLocalGroupDelMembers(None, group, 3,[ug_info])
            return None
        except win32net.error as error:
            errno, errctx, errmsg = error.args
            return errmsg

    def __modify(self, work):
        res = etree.element("wu",
                            id=work.attrib["id"])

        # Insert work here.

        res.attrib["status"] = "success"
        return res

    def __order(self, work):
        pass

    def __remove(self, work):
        res = etree.element("wu",
                            id=work.attrib["id"])

        # Insert work here.

        res.attrib["status"] = "success"
        return res

    def __add(self, work):
        res = etree.element("wu",
                            id=work.attrib["id"])

            res.attrib["status"] = "success"
            
        return res

    def generate_status(self):
        c = wmi.WMI()
        root = etree.Element("usergroup")
        sysname = uname()[1]
        
        # Build a list of local group elements
        for group in c.Win32_Group(LocalAccount=True):
            g_elt = etree.Element("group")
            g_elt.attrib["id"] = group.Name
            # Get a list of group members
            members, count, handle = win32net.NetLocalGroupGetMembers(None,
                                                               group.Name,
                                                               3)
            for member in members:
                # Member is a dictionary, thanks to the windows API.
                domname = member["domainandname"].split('\\')
                m_elt = etree.Element("member")
                if domname[0].upper() != sysname.upper():
                    m_elt.attrib["domain"] = domname[0]
                m_elt.attrib["id"] = domname[1]
                g_elt.append(m_elt)
                
            # We're only interested in groups with members
            if len(g_elt) > 0: root.append(g_elt)
        
        # Iterate over local user elements only
        for user in c.Win32_UserAccount(LocalAccount=True):
            u_elt = etree.Element("user")
            u_elt.attrib["id"] = user.Name
            u_elt.attrib["password_can_expire"] = int(i.PasswordExpires)
            d = etree.Element("Description")
            d.text = user.Description
            u_elt.append(d)
            root.append(u_elt)

        return root
        