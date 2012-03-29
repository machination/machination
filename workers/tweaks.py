#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A worker for Machination functions not deemed important enough to have
their own worker.

Currently only handles NTP (enable/disable and ser server)."""

from lxml import etree
import wmi
import machination

class tweaks():
    logger = None
    utils = None
    #Define a shorthand constant for HKLM.
    _HLKM = 2147483650
    
    def __init__(self, config_elt):
        self.logger = machination.logger.Logger(config_elt)

    def do_work(self, work_list):
        "Iterates over the work list, currently only handles time functions."
        for item in work_list[0]:
            if item.tag == "NtpEnabled":
                timeconfig[item.tag] = item.value
            elif item.tag[:-1] == "TimeServer":
                timeconfig["TimeServer"].append(item.value)
            else:
                message = "Undefined work unit for tweaks: {0} {1}".format(
                    item.tag,
                    item.value)
                logger.wmsg(message)
                
        self._doTimeSetting(todo)

    def _doTimeSetting(self, settings):
        # Set time servers first
        logger.lsmg("Setting time servers")
        r = wmi.Registry()
        srvkeyname = "SOFTWARE/Microsoft/Windows/CurrentVersion/DateTime/Servers"
        
        # FIXME set the default value under srvkeyname to 1
        
        # Set individual time servers
        for i in (1,2,3):
            val = settings["TimeServer"][(i-1)]
            result = r.SetStringValue(
                hDefKey=_HKLM,
                sSubKeyName=srvkeyname,
                sValueName=str(i),
                sValue=val)
            if result:
                # Registry write failed
                logger.emsg("Failed to set Timeserver{0}".format(i))
            else:
                logger.lmsg("Timeservers: {1}\n{0}{2}\n{0}{3}".format(
                " "*13,
                settings["TimeServer"][0],
                settings["TimeServer"][1],
                settings["TimeServer"][2]), 4)
        
        # Define values to registry-twiddle the time settings
        timesetloc = "System/CurrentControlSet/Services/W32Time/Parameters"
        serverval = "{0},0x1".format(settings["TimeServer"][0])
        
        # Set default time server
        result = r.SetStringValue(
            hDefKey=_HKLM,
            sSubKeyName=timesetloc,
            sValueName="NtpServer",
            sValue=serverval)
        if result:
            # Registry write failed
            logger.emsg("Failed to set default Timeserver: {0}".format(result))

        # Enable or disable NTP as necessary.
        if settings["NtpEnabled"] == "True":
            logger.lmsg("Enabling NTP Time Synchronisation")
            result = r.SetStringValue(
                hDefKey=_HKLM,
                sSubKeyName=timesetloc,
                sValueName="Type",
                sValue="NTP")
            if result:
                logger.emsg("Could not set NTP: {0}".format(result))
        else:
            logger.lmsg("Disabling NTP Time Synchronisation")
            result = r.SetStringValue(
                hDefKey=_HKLM,
                sSubKeyName=timesetloc,
                sValueName="Type",
                sValue="NoSync")
            if result:
                logger.emsg("Could not set NTP: {0}".format(result))

    def generate_status(self):
        timestat = _gen_time_status()
        time = etree.Element("Time")
        for key, value in timestat.items():
            elem = etree.Element(key)
            elem.text = value
            time.append(elem)
        return time

    def _gen_time_status(self):
        stat = {}
        
        r = wmi.Registry()
        
        ntpstatloc = "System/CurrentControlSet/Services/W32Time/Parameters"
        timesrvloc = "SOFTWARE/Microsoft/Windows/CurrentVersion/DateTime/Servers"
        result, value = r.GetStringValue(
            hDefKey=_HKLM,
            sSubKeyName=ntpstatloc,
            sValueName="Type")
        if result:
            # Registry read failed
            logger.emsg("Could not read NTP status")
        else:
            if value == "NTP":
                stat["NtpEnabled"] = "True"
            elif value == "NoSync":
                stat["NtpEnabled"] = "False"
        
        for i in (1,2,3):
            valname = "{0}".format(i)
            result, value = r.GetStringValue(
                hDefKey=_HKLM,
                sSubKeyName=timesrvloc,
                sValueName=valname)
            if result:
                # Registry read failed
                logger.emsg("Could not read NTP Server {0}".format(i))
            else:
                keyname = "TimeServer{0}".format(i)
                stat[keyname] = value
        
        return stat
        