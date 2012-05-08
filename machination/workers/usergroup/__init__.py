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


class worker(object):
    
    def __init__(self):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix = '/status')
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

        
    def do_work(self, work_list):
        "Process the work units and return their status."
        result = []
        for wu in work_list:
            operator = "__{}".format(wu.attrib["op"])
            res = getattr(self, operator)(wu)
            result.append(res)
        return result

    def __add_user(self, username, password, expire, description):
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

    def __mod_user(self, user, expire, description):
        info = win32net.NetUserGetInfo(None, user, 3)
        
        if expire is not None:
            info["flags"] |= win32netcon.UF_DONT_EXPIRE_PASSWD
        if description is not None:
            info["description"] = description
            
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

    def __check_group(self, g_name):
        c = wmi.WMI()
        extant = c.Win32_Group(Name=g_name, LocalAccount=True)
        back = None
        if not extant:
            back = add_group(g_name)
        return back

    def __check_group_rm(self, g_name):
        members, count, handle = win32net.NetLocalGroupGetMembers(None,
                                                               g_Name,
                                                               3)
        back = None
        if (count == 0) and (g_name not in sp_groups):
            back = self.__del_group(g_name)
        return back

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
    
    def __get_group_name(self, xpath):
        mrx = machination.xmltools.MRXpath(xpath)
        mrx = mrx.parent()
        return mrx.id()

    def __add(self, work):
        res = etree.element("wu",
                            id=work.attrib["id"])

        if work[0].tag == "user":
            u_name = work[0].attrib["id"]
            u_pwd = " ".join(work[0].xpath('/user/initialPassword/text()',
                                           smart_strings=False))
            u_desc = " ".join(work[0].xpath('/user/description/text()',
                                            smart_strings=False))
            u_expire = work[0].attrib["password_can_expire"]
            test = self.__add_user(u_name, u_pwd, u_expire, u_desc)
        elif work[0].tag == "member":
            group = self.__get_group_name(work.attrib["id"])
            test = self.__check_group(group)
            
            if not test:
                m_name = work[0].attrib["id"]
                if "domain" in work[0].attrib:
                    m_dom = work[0].attrib["domain"]
                else:
                    m_dom = None
                test = self.__add_user_to_group(m_name, group, m_dom)

        res.attrib["status"] = "success"
        if test:
            emsg(test)
            res.attrib["status"] = "error"
            res.attrib["message"] = test
            
        return res

    def __remove(self, work):
        res = etree.element("wu",
                            id=work.attrib["id"])

        if work[0].tag == "user":
            u_name = work[0].attrib["id"]
            test = self.__del_user(u_name)
        elif work[0].tag == "member":
            group = self.__get_group_name(work.attrib["id"])
            m_name = work[0].attrib["id"]
            if "domain" in work[0].attrib:
                m_dom = work[0].attrib["domain"]
            else:
                m_dom = None
            test = self.__del_user_from_group(m_name, group, m_dom)
            if not test:
                # Delete went smoothly. Can we delete the group?
                test = self.__check_group_rm(group)

        res.attrib["status"] = "success"
        if test:
            emsg(test)
            res.attrib["status"] = "error"
            res.attrib["message"] = test

        return res

    def __modify(self, work):
        res = etree.element("wu",
                            id=work.attrib["id"])

        # As far as I can work out, we can only modify users, not groups
        if work[0].tag == "member":
            test = "Can't modify group, only add or remove members" 
        else:
            c = wmi.WMI()
            [user] = c.Win32_UserAccount(LocalAccount=True,
                                       Name=work[0].attrib["id"])
            expire = work[0].attrib["password_can_expire"]
            desc = " ".join(work[0].xpath('/user/description/text()',
                                          smart_strings=False))
            # Set whatever hasn't changed to None
            if int(user.PasswordExpires) == expire:
                expire = None
            if user.Description == desc:
                desc = None
            test = self.__mod_user(user.Name, expire, desc)

        res.attrib["status"] = "success"

        if test:
            emsg(test)
            res.attrib["status"] = "error"
            res.attrib["message"] = test

        return res

    def __order(self, work):
        pass

    def generate_status(self):
        c = wmi.WMI()
        w_elt = etree.Element("usergroup")
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
            if len(g_elt) > 0: w_elt.append(g_elt)
        
        # Iterate over local user elements only
        for user in c.Win32_UserAccount(LocalAccount=True):
            u_elt = etree.Element("user")
            u_elt.attrib["id"] = user.Name
            u_elt.attrib["password_can_expire"] = int(user.PasswordExpires)
            d = etree.Element("Description")
            d.text = user.Description
            u_elt.append(d)
            w_elt.append(u_elt)

        return w_elt
        