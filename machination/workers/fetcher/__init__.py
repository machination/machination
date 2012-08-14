"Wraps the fetcher in a worker"

from lxml import etree
from machination import context
from machination import xmltools
from time import sleep
import urllib.request
import urllib.error
import os
import errno
import sys
import hashlib


class Worker(object):
    """Fetch tagged bundles from sources defined in config

    """

    def __init__(self):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')
        self.config_elt = self.read_config()
        self.pad_elt = etree.Element("status")

    def read_config(self):
        config_file = os.path.join(context.conf_dir(), "fetcher.xml")
        try:
            c_elt = etree.Parse(config_file)
        except IOError as e:
            c_elt = etree.Element("config")
        return c_elt

    def write_config(self):
        config_file = os.path.join(context.conf_dir(), "fetcher.xml")
        with open(config_file, 'w') as c:
            c.write(etree.tostring(self.config_elt,
                                   pretty_print=True)
                   )

    def do_work(self, work_list):
        "Process the work units and return their status."

        # Setup
        result = []
        flag = False
        pref = "/status/worker[@id='fetcher']"
        confcheck = ''.join(pref, "/config")

        for wu in work_list:
            if wu.attrib["id"].startswith(confcheck):
                xmltools.apply_wu(wu,
                                  self.config_elt,
                                  strip=pref)
                flag = True
                res = etree.Element("wu",
                                    id=work.wu.attrib["id"]
                                    status="success")
            else:
                operator = "__{}".format(wu.attrib["op"])
                res = getattr(self, operator)(wu)
            result.append(res)

        # Finished all work. Write config file if changed
        if flag:
            self.write_config()

        return result

    def __add(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])
        # Where are we getting it from?
        for source in self.config_elt.xpath('config/sources/*'):
            transport = "__download_{}".format(source.attrib["mechanism"])
            out = getattr(self, transport)(source, work)
            if out == None:
                continue
            elif out.startswith("Failed"):
                res.attrib["status"] = "error"
                res.attrib["message"] = out
            else:
                res.attrib["status"] = success
            return res

        # no suitable source
        context.emsg("No suitable source defined")
        res.attrib["status"] = "error"
        res.attrib["message"] = "No suitable source defined"

    def __download_urllib(self, source, work):
        # Construct URL
        baseurl = source.attrib["URL"] + '/' + work[0].attrib["id"]
        manifest = baseurl + '/manifest'
        context.dmsg("Downloading manifest: " + manifest)
        try:
            m = urllib.request.urlopen(manifest)
        except urllib.error.HTTPError as e:
            reason = "HTTP Error: " + e.code
        except urllib.error.URLError as e:
            reason = "URL Error: " + e.reason
        if reason:
            context.emsg(reason)
            return "Failed: " + reason

        # Set destination
        c = config_elt.xpath('config/cache[@location]'):
        if c:
            cache_loc = c[0].attrib["location"]
        else:
            cache_loc = "files"

        dest = os.path.join(context.cache_dir(),
                            cache_loc,
                            '.' + work[0].attrib["id"])
        f_dest = os.path.join(context.cache_dir(),
                              cache_loc,
                              work[0].attrib["id"])
        # Assume a sensible umask for now...
        os.mkdir(dest)

        context.dmsg("Downloading files")
        # Set up hash
        sha = hashlib.sha512()
        for file in m:
            f = baseurl + '/' + file.strip
            context.dmsg("Downloading file: " + f, 8)

            target = os.path.join(dest, f)
            if not os.path.exists(os.path.dirname(target):
                os.mkdir(os.path.dirname(target)

            if config_elt.xpath('config/retry'):
                num = config_elt.xpath('config/retry')[0].attrib["number"]
                ttw = config_elt.xpath('config/retry')[0].attrib["time_to_wait"]
            else:
                num = 1
                ttw = 30

            while True:
                try:
                    a = urllib.request.urlopen(f)
                    break
                except urllib.error.HTTPError as e:
                    if num == 0:
                        wmsg("HTTP Error " + e.code + " Retrying in " + ttw + " seconds")
                        num -= 1
                        sleep(ttw)
                    else:
                        msg = "Failed: HTTP Error: " + e.code
                        emsg(msg)
                        return msg


            with open(target, 'wb') as b:
                tmp = a.read()
                sha.update(tmp)
                b.write(tmp)

        if not work[0].attrib["id"].endswith('nohash')
            hash = work[0].attrib["id"].split('-',1)[1]
            if hash != sha.hexdigest():
                context.emsg("Hash failure")
                return "Failed: Hash failure"

        os.rename(dest, f_dest)
        context.dmsg('Download Successful')
        return "Download Successful"

    def __download_torrent(self, source, work):
        return "Failed: Torrent download not supported."

    def __remove(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])
        res.attrib["status"] = success
        return res

    def __move(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])
        res.attrib["status"] = success
        return res

    def __datamod(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])
        res.attrib["status"] = success
        return res

    def __deepmod(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])
        res.attrib["status"] = success
        return res



    def generate_status(self):
        w_elt = etree.Element("worker")
        w_elt.set("id", self.name)

        return w_elt

    def do_work(self, wus):
        results = []
