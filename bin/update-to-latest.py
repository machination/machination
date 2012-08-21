import subprocess
import os
import argparse
import shutil
import platform
import logging
import sys
import re
from lxml import etree
import wmi

logging.basicConfig(level=logging.DEBUG)

def_bdir = '/tmp'
bdist_cmd = 'bdist_deb'
if platform.system() == 'Windows':
    def_bdir = 'c:\\workspace\\bundles'
    bdist_cmd = 'bdist_msi'

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('gitdir', nargs='?', default='.',
                    help='repository with packages')
parser.add_argument('--bundle_dir', '-b', nargs='?', default = def_bdir,
                    help='directory in which to make fake bundles')
args = parser.parse_args()

# get version
gitver = subprocess.check_output(
    ['git', '--git-dir', os.path.join(args.gitdir, '.git'),
     'describe', '--tags', '--long' ],
    shell=True
    ).strip().decode()

vlist = gitver.split('-')
vlist.pop()
commits = vlist.pop()
version = '{}.{}'.format('-'.join(vlist), commits)

# Clean dist
distdir = os.path.join(args.gitdir, 'dist')
for f in os.listdir(distdir):
    fpath = os.path.join(distdir, f)
    if os.path.isfile(fpath) and f.startswith('machination-client'):
        logging.info('cleaning pkg {}'.format(f))
#        os.remove(fpath)

# Clean bundles
for d in os.listdir(args.bundle_dir):
    dpath = os.path.join(args.bundle_dir, d)
    if os.path.isdir(dpath) and d. startswith('machination-client'):
        logging.info('cleaning bundle {}'.format(d))
        shutil.rmtree(dpath)

# Make new packages
#subprocess.check_call(
#    [sys.executable,
#     os.path.join(args.gitdir, 'setup.py'),
#     bdist_cmd]
#    )

# Clean .egg_info dirs
for d in os.listdir(args.gitdir):
    dpath = os.path.join(args.gitdir, d)
    if os.path.isdir(dpath) and d. endswith('.egg-info'):
        logging.info('cleaning egg-info {}'.format(d))
        shutil.rmtree(dpath)

# Make bundles
pkgids = []
for f in os.listdir(distdir):
    fpath = os.path.join(distdir, f)
#    logging.debug('testing {} for pkgid'.format(f))
    m = re.match(r'(machination-client-.*)-{}'.format(version), f)
    pkgname = m.group(1)
    logging.info('bundling {} version {}'.format(pkgname, version))
    pkgid = '{}-{}'.format(pkgname, version)
    pkgids.append(pkgid)
    os.mkdir(os.path.join(args.bundle_dir, pkgid))
    os.mkdir(os.path.join(args.bundle_dir, pkgid, 'files'))
    shutil.copy(fpath, os.path.join(args.bundle_dir, pkgid, 'files'))

# Construct installed_version.xml
iv = etree.Element('iv', budleDir = args.bundle_dir)
current = etree.Element('installedVersion', version='current')
desired = etree.Element('installedVersion', version='desired')
# desired from pkgids
for pkgid in pkgids:
    desired.append(
        etree.Element('machinationFetcherBundle', id = pkgid)
        )
# current from system
# TODO(colin): support other OSes
con = wmi.WMI()
for prod in con.query(
    "select * from Win32Product where Name like 'Python machination-client%'"
    ):
    current.append(etree.Element('machinationFetcherBundle', id=prod.Name[7:]))
iv.append(current)
iv.append(desired)
# write to file
with open('iv.xml', "w") as ivf:
    ivf.write(etree.tostring(iv))

# invoke self update
os.execl(
    sys.executable,
    os.path.join(args.gitdir, 'bin', 'machination-self-update.py'),
    'iv.xml'
    )
