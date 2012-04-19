#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker to create/modify user accounts and groups in Windows."""


from lxml import etree
import machination
import win32netcon
import win32com.client
import win32net
import wmi


class usergroup(object):
    logger = None
    
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

    def __init__(self, logger):
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
        description += " machination-controlled"
        u = {"name": username,
             "password": password,
             "comment": description,
             "flags": win32netcon.UF_NORMAL_ACCOUNT | win32netcon.UFSCRIPT,
             "priv": win32netcon.UF_PRIV_USER
            }

        if expire = 0:
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
            if k = "password_can_expire":
                info["flags"] |= win32netcon.UF_DONT_EXPIRE_PASSWD
            elif k = "initialPassword":
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
            return "Cannot add a defined special group"

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

    def __add_user_to_group(self, user, group):
        ug_info = {"domainandname": user}
        try:
            win32net.NetLocalGroupAddMembers(None, group, 3,[ug_info])
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

        if work[0].tag = "user":
            u_name = work[0].attrib["id"]
            u_pwd = work[0].attrib["password_can_expire"]
            u_pass = work[0].iter("initialPassword")[0].text
            if work[0].iter("description"):
                u_desc = work[0].iter("description")
            else:
                u_desc = None

            self.__add_user(u_name, u_pass, u_pwd, u_desc)

        elif work[0].tag = "group":
            back = self.__add_user(work[0])
        else:
            back = "Unknown element defined: " + work[0].tag

        if back:
            wmsg(back)
            res.attrib["status"] = "error"
            res.attrib["message"] = back
        else:
            res.attrib["status"] = "success"
            
        return res

    def generate_status(self):
        root = wmi.WMI()
        out = etree.Element("usergroup")
        
        for group in c.Win32_Group(LocalAccount=True):
            g_elt = etree.Element("group")
            g_elt.attrib["id"] = group.Name
            root.append(g_elt)
        
        for user in c.Win32_UserAccount(LocalAccount=True):
            if user.Name not in sp_users:
                u_elt = etree.Element("user")
                u_elt.attrib["id"] = user.Name
                u_elt.attrib["password_can_expire"] = int(i.PasswordExpires)
                d = etree.Element("Description")
                d.text = user.Description
                u_elt.append(d)
                root.append(u_elt)
            grplst = win32net.NetUserGetLocalGroups(None, user.Name)
            for grp in root.iter("group"):
                if grp.attrib["id"] in grplist:
                    m_elt = etree.Element("member")
                    m_elt.attrib["id"] = user.Name

        