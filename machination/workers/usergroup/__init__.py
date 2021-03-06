#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker to create/modify user accounts and groups in Windows."""

from lxml import etree
from machination import context
import win32netcon
import win32com.client
import win32net
import wmi
from platform import uname

l = context.logger

class Worker(object):

    def __init__(self):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')
        self.sp_users = ("Administrator",
                    "ASPNET",
                    "Guest",
                    "HelpAssistant",
                    "SUPPORT_388945a0")

        self.sp_groups = ("Administrators",
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
            if wu[0].tag not in ["user", "group"]:
                msg = "Work unit of type: " + wu[0].tag
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

    def _add_user(self, username, password, expire, description):
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

    def _mod_user(self, user, expire, description):
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

    def _del_user(self, username):
        # Don't ever delete special user accounts
        if username in self.sp_users:
            return None
        try:
            win32net.NetUserDel(None, username)
            return None
        except win32net.error as error:
            errno, errctx, errmsg = error.args
            return errmsg

    def _add_group(self, name):
        g_info = {"name": name}

        if name in self.sp_groups:
            return "Cannot add a special group"
        try:
            win32net.NetLocalGroupAdd(None, 1, g_info)
            return None
        except win32net.error as error:
            errno, errctx, errmsg = error.args
            return errmsg

    def _check_group(self, g_name):
        c = wmi.WMI()
        extant = c.Win32_Group(Name=g_name, LocalAccount=True)
        back = None
        if not extant:
            back = add_group(g_name)
        return back

    def _check_group_rm(self, g_name):
        members, count, handle = win32net.NetLocalGroupGetMembers(None,
                                                               g_name,
                                                               3)
        back = None
        if count == 0 and g_name not in self.sp_groups:
            back = self._del_group(g_name)
        return back

    def _del_group(self, name):
        if name in self.sp_groups:
            return None
        try:
            win32net.NetLocalGroupDel(None, name)
            return None
        except win32net.error as error:
            errno, errctx, errmsg = error.args
            return errmsg

    def _add_user_to_group(self, user, group, domain=None):
        if domain:
            userstring = u"\\".join([domain.upper(), user])
        else:
            userstring = user

        ug_info = {"domainandname": userstring}

        try:
            win32net.NetLocalGroupAddMembers(None, group, 3, [ug_info])
            return None
        except win32net.error as error:
            errno, errctx, errmsg = error.args
            return errmsg

    def _del_user_from_group(self, user, group, domain=None):
        if domain:
            userstring = u"\\".join([domain.upper(), user])
        else:
            userstring = user

        ug_info = {"domainandname": userstring}
        try:
            win32net.NetLocalGroupDelMembers(None, group, 3, [ug_info])
            return None
        except win32net.error as error:
            errno, errctx, errmsg = error.args
            return errmsg

    def _get_group_name(self, xpath):
        mrx = machination.xmltools.MRXpath(xpath)
        mrx = mrx.parent()
        return mrx.id()

    def _add(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])

        if work[0].tag == "user":
            u_name = work[0].attrib["id"]
            u_pwd = " ".join(work[0].xpath('/user/initialPassword/text()',
                                           smart_strings=False))
            u_desc = " ".join(work[0].xpath('/user/description/text()',
                                            smart_strings=False))
            u_expire = work[0].attrib["password_can_expire"]
            test = self._add_user(u_name, u_pwd, u_expire, u_desc)
        elif work[0].tag == "member":
            group = self._get_group_name(work.attrib["id"])
            test = self._check_group(group)

            if not test:
                m_name = work[0].attrib["id"]
                if "domain" in work[0].attrib:
                    m_dom = work[0].attrib["domain"]
                else:
                    m_dom = None
                test = self._add_user_to_group(m_name, group, m_dom)

        res.attrib["status"] = "success"
        if test:
            l.emsg(test)
            res.attrib["status"] = "error"
            res.attrib["message"] = test

        return res

    def _remove(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])

        if work[0].tag == "user":
            u_name = work[0].attrib["id"]
            test = self._del_user(u_name)
        elif work[0].tag == "member":
            group = self._get_group_name(work.attrib["id"])
            m_name = work[0].attrib["id"]
            if "domain" in work[0].attrib:
                m_dom = work[0].attrib["domain"]
            else:
                m_dom = None
            test = self._del_user_from_group(m_name, group, m_dom)
            if not test:
                # Delete went smoothly. Can we delete the group?
                test = self._check_group_rm(group)

        res.attrib["status"] = "success"
        if test:
            l.emsg(test)
            res.attrib["status"] = "error"
            res.attrib["message"] = test

        return res

    def _deepmod(self, work):
        res = etree.Element("wu",
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
            test = self._mod_user(user.Name, expire, desc)

        res.attrib["status"] = "success"

        if test:
            l.emsg(test)
            res.attrib["status"] = "error"
            res.attrib["message"] = test

        return res

    def _datamod(self, work):
        return self._deepmod(work)
