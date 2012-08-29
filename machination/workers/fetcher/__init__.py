#!/usr/bin/python
# vim: set fileencoding=utf-8:

"A worker to fetch Machination bundles"

from lxml import etree
from machination import context
from machination import xmltools
from machination.xmltools import MRXpath
from time import sleep
import urllib.request
import urllib.error
import os
import stat
import shutil
import errno
import sys
import hashlib
import platform
import glob

l = context.logger

class Worker(object):
    """Fetch tagged bundles from sources defined in config"""

    # set up size maps as log(1024)
    s_maps = {'B': 0,
              'K': 1,
              'M': 2,
              'G': 3,
              'T': 4}

    def __init__(self):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')
        self.config_elt = self.read_config()
        self.cache_maint()

    def list_bundles(self):
        return [
            d for d in os.listdir(self.cache_dir)
            if os.path.isdir(os.path.join(self.cache_dir, d))
        ]

    def cache_maint(self):
        l.lmsg("Cleaning fetcher cache.")

        cache_elt = self.config_elt.xpath('config/cache[@size]')
        if not cache_elt:
            return None
        else:
            size = cache_elt[0].attrib["size"]

        # List all the bundle directories in order of mtime
        bdl = [os.path.join(self.cache_dir, f) for f in self.list_bundles]
        bdl.sort(key=lambda x: os.path.getmtime(x))

        while self.cache_over_limit(size):
            try:
                a = bdl.pop(0)
            except IndexError as e:
                msg = "Cache cannot be brought below limit"
                l.wmsg(msg)
                break
            # Ignore files that are kept, that have already been cleaned,
            # or that aren't yet done.
            if os.path.exists(os.path.join(a, '.keep')):
                continue
            if not os.path.exists(os.path.join(a, 'files')):
                continue
            if not os.path.exists(os.path.join(a, '.done')):
                continue
            shutil.rmtree(os.path.join(a, 'files'))
        return None

    def handleRemoveReadOnly(self, func, path, exc):
        excvalue = exc[1]
        if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCESS:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.IRWXO)
            func(path)
        else:
            raise

    def cache_over_limit(self, size):
        cache_size = size(self.cache_dir)
        if size[-1] == '%':
            op = 'space_' + platform.system()
            disk_size = getattr(self, op)(self.cache_dir, 'total')
            percent = int(size[:-1])
            left = (cache_size / disk_size) * 100
            right = percent
        else:
            # Size in bytes has either B/K/M/G/T as final character indicating
            # bytes, kb, mb, gb, etc.
            size_in_bytes = int(size[:-1]) * 1024**s_maps[size[-1]]
            left = cache_size
            right = size_in_bytes
        return left > right

    def space_Windows(self, disk='C', type='total'):
        if type not in ['total', 'free']:
            raise ValueError("type must be either 'total' or 'free'")
        import wmi
        w = wmi.WMI()
        for drive in w.Win32_LogicalDisk():
            if drive.Caption[0] == disk[0]:
                if type=='total':
                    return int(drive.Size)
                else:
                    return int(drive.FreeSpace)
        else:
            raise ValueError("specified disk " + disk + "does not exist")

    def space_Linux(self, disk='/', type='total'):
        if type not in ['total', 'free']:
            raise ValueError("type must be either 'total' or 'free'")

        s = os.statvfs(dir)
        if type=='total':
            return (s.f_bavail * s.f_frsize)
        else:
            return (s.f_blocks * s.f_frsize)

    def size(self, start_path='.'):
        total = 0
        for root, dirs, files in os.walk(start_path):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
        return total

    def read_config(self):
        config_file = os.path.join(context.conf_dir(), "fetcher.xml")
        try:
            c_elt = etree.parse(config_file).getroot()
        except:
            c_elt = etree.Element("config")

        self.cache_dir = os.path.join(context.cache_dir(), "bundles")
        try:
            os.mkdir(self.cache_dir)
        except OSError as e:
            if e.errno == errno.EEXIST:
                # don't worry about it
                pass

        return c_elt

    def write_config(self):
        config_file = os.path.join(context.conf_dir(), "fetcher.xml")
        with open(config_file, 'w') as c:
            c.write(etree.tostring(self.config_elt,
                                   pretty_print=True).decode()
                   )

    def do_work(self, work_list):
        "Process the work units and return their status."

        # Setup
        result = []
        flag = False
        pref_mrx = MRXpath("/status/worker[@id='fetcher']")

        for wu in work_list:
            if len(wu) != 0:
                if wu[0].tag not in ["bundle", "config"]:
                    msg = "Work unit of type: " + wu[0].tag
                    msg += " not understood by fetcher. Failing."
                    l.emsg(msg)
                    res = etree.Element("wu",
                                        id=wu.attrib["id"],
                                        status="error",
                                        message=msg)
                    continue
            wu_mrx = MRXpath(wu.attrib["id"])
            if wu_mrx.name() == "config":
                self.config_elt = xmltools.apply_wu(
                    wu,
                    self.config_elt,
                    prefix=pref_mrx
                    )
                flag = True
                res = etree.Element("wu",
                                    id=wu.attrib["id"],
                                    status="success")
            else:
                operator = "_{}".format(wu.attrib["op"])
                res = getattr(self, operator)(wu)
            result.append(res)

        # Finished all work. Write config file if changed
        if flag:
            self.write_config()

        return result

    def _add(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])
        # Have we already got it?
        target = os.path.join(self.cache_dir, work[0].attrib["id"])
        if os.path.isdir(target):
            # Successful download already happened
            msg = "Bundle directory already exists."
            l.emsg(msg)
            res.attrib["status"] = "error"
            res.attrib["message"] = msg
            return res

        # Where are we getting it from?
        for source in self.config_elt.xpath('source'):
            transport = "_download_{}".format(source.attrib["mechanism"])
            l.lmsg(" ".join(["Trying to download via",
                             source.attrib["mechanism"],
                             "from",
                             source.attrib["url"]]))
            out = getattr(self, transport)(source, work)
            if out == None:
                l.wmsg("No handler for " + source.attrib["mechanism"])
            elif out.startswith("Failed"):
                l.wmsg("Download from " + source.attrib["url"] + " failed")
                l.wmsg(out)
            else:
                res.attrib["status"] = "success"
                break
        else:
            # no suitable source
            l.emsg("No suitable source defined")
            res.attrib["status"] = "error"
            res.attrib["message"] = "No suitable source defined"

        return res

    def _download_urllib(self, source, work):
        # Construct URL & retry parameters
        baseurl = source.attrib["url"] + '/' + work[0].attrib["id"]
        manifest = baseurl + '/manifest'
        if self.config_elt.xpath('retry'):
            retry = self.config_elt.xpath('retry/@number')[0]
            ttw = self.config_elt.xpath('retry/@time_to_wait')[0]
        else:
            retry = 1
            ttw = 30

        # Set destination
        dest = os.path.join(self.cache_dir, '.' + work[0].attrib["id"])

        # Set up directory structure
        try:
            os.mkdir(dest)
        except WindowsError as e:
            if e.errno == 183:
                # 183 means file/dir exists
                pass
        except OSError as e:
            if e.errno == errno.EEXIST:
                # not worried
                pass
        except:
            return 'Failed: something went wrong constructing cache dir'

        # Get the manifest and put into specials
        l.dmsg("Downloading manifest: " + manifest)
        reason = None
        try:
            m = urllib.request.urlopen(manifest)
        except urllib.error.HTTPError as e:
            reason = "HTTP Error: " + str(e.code)
        except urllib.error.URLError as e:
            reason = "URL Error: " + e.reason

        if reason:
            shutil.rmtree(dest),
            l.emsg(reason)
            return "Failed: " + reason

        # Parse the manifest
        # FIXME: Assumes utf-8 encoding

        pkg_size = int(m.readline().decode('utf-8').strip())
        pkg = [x.decode('utf-8').strip() for x in m.readlines()]

        m.close()

        mani_path = os.path.join(dest, 'manifest')
        with open(mani_path, 'w') as f:
            f.write(str(pkg_size) + "\n")
            for x in pkg:
                f.write(x + "\n")


        # Check free space
        l.dmsg(str(pkg_size) + " bytes to download.")
        op = 'space_' + platform.system()
        if pkg_size > getattr(self, op)(self.cache_dir, 'free'):
            self.cache_maint()
            if pkg_size > getattr(self, op)(self.cache_dir,'free'):
                msg = "Not enough free space in package cache."
                l.emsg(msg)
                return "Failed: " + msg

        l.dmsg("Downloading files")

        # Set up hash
        h_flag = False
        if "hash" in pkg:
            sha = hashlib.sha512()
            h_flag = True

        # Main download loop
        for file in pkg:
            fileurl = baseurl + '/' + file
            l.dmsg("Downloading file: " + fileurl, 8)

            target = os.path.join(dest, file)
            if not os.path.exists(os.path.dirname(target)):
                os.mkdir(os.path.dirname(target))

            # Download the file. Retry and ttw are for resiliancy
            num = retry
            while True:
                try:
                    a = urllib.request.urlopen(fileurl)
                    break
                except urllib.error.HTTPError as e:
                    if num == 0:
                        wmsg("HTTP Error " + str(e.code) +
                             " Retrying in " + ttw + " seconds")
                        num -= 1
                        sleep(ttw)
                    else:
                        msg = "Failed: HTTP Error: " + str(e.code)
                        emsg(msg)
                        return msg

            # Hash and write the file.
            with open(target, 'wb') as b:
                tmp = a.read()
                if h_flag and file != "hash":
                    sha.update(tmp)
                b.write(tmp)

            a.close()

        # Check the package hash
        if h_flag:
            with open(os.path.join(dest, 'hash'), 'r') as h:
              hash = h.read()
            if hash != sha.hexdigest():
                w.emsg("Hash failure")
                d.emsg("Hash file: " + hash)
                d.emsg("Hexdigest: " + sha.hexdigest())
                shutil.rmtree(dest)
                return "Failed: Hash failure"
            else:
              d.lmsg("Hash check successful")
        if work[0].get("keep") == "1":
            open(os.path.join(dest, '.keep'), 'a').close()

        # Move to the 'real' bundle directory
        (dir, id) = os.path.split(dest)
        f_dest = os.path.join(dir, id[1:])
        os.rename(dest, f_dest)

        l.dmsg('Download Successful')
        return "Download Successful"

    def _download_torrent(self, source, work):
        pass

    def _remove(self, work):
        print(etree.tostring(work,pretty_print=True).decode())
        res = etree.Element("wu",
                            id=work.attrib["id"])
        # Deconstruct wu xpath
        wu_mrx = MRXpath(work.attrib["id"])
        bundle_id = wu_mrx.id()

        # Identify package directory
        dest = os.path.join(self.cache_dir, bundle_id)

        # Fail if not exist
        if not os.path.isdir(dest):
            msg = "Package directory does not exist"
            l.emsg(msg)
            res.attrib["status"] = "error"
            res.attrib["message"] = msg

        # Nuke the directory
        try:
            shutil.rmtree(dest)
            res.attrib["status"] = success
        except:
            msg = "Could not remove package directory."
            l.emsg(msg)
            res.attrib["status"] = "error"
            res.attrib["message"] = msg

        return res

    def _datamod(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])
        res.attrib["status"] = success
        return res

    def _deepmod(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"],
                            status="success")

        bundle = work[0].attrib["id"]
        bundle_dir = os.path.join(self.cache_dir, bundle)
        if not os.path.isdir(bundle_dir):
            msg = "Error: Bundle not found: " + bundle_dir
            l.emsg(msg)
            res.attrib["status"] = "error"
            res.attrib["message"] = msg
            return res

        old = os.path.exists(os.path.join(bundle_dir, '.keep'))
        new = work[0].attrib["keep"] == '1'

        if old ^ new:
            # Keep has changed
            if old:
                # Keep is now 0
                os.remove(os.path.join(bundle_dir, '.keep'))
            if new:
                # Keep is now 1
                if os.path.isdir(os.path.join(bundle_dir, 'files')):
                    #Cache not cleaned
                    open(os.path.join(bundle_dir, '.keep'), 'a').close()
                else:
                    #Cache cleaned
                    msg = "Keep attribute set for cleaned bundle."
                    l.wmsg(msg)
                    specials = os.path.join(bundle_dir, 'special')
                    if os.path.exists(os.path.join(bundle_dir, '.done')):
                        done = True
                    shutil.move(specials, os.path.join(self.cache_loc, '_tmp'))
                    d = self._remove(work)
                    if d.attrib["status"] != "success":
                        l.emsg("Bundle remove failed.")
                        return d
                    d = self._add(work)
                    if d.attrib["status"] != "success":
                        l.emsg("Bundle re-download failed.")
                        return d
                    shutil.move(os.path.join(self.cache_loc, '_tmp'), specials)
                    if done:
                        open(os.path.join(bundle_dir, '.done'), 'a').close()

        return res

    def generate_status(self):
        w_elt = etree.Element("worker")
        w_elt.set("id", self.name)

        # First subelement is config
        w_elt.append(self.config_elt)

        # Loop through bundle elements.

        for bundle in self.list_bundles():
            if bundle[0] == ".":
              continue

            b_elt = etree.SubElement(w_elt, "bundle", id=bundle)

            if os.path.exists(os.path.join(self.cache_dir,bundle,'.keep')):
                b_elt.attrib["keep"] = "1"

            if not os.path.isdir(os.path.join(self.cache_dir,bundle,'files')):
                b_elt.attrib["cleaned"] = "1"

        return w_elt
