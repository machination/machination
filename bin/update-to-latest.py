#!/usr/bin/python

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
import glob

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
parser.add_argument('--update', '-u', nargs='?', default = '1',
                    help='whether to perform the update or not')
args = parser.parse_args()

# get git version
gitver = subprocess.check_output(
    ['git', '--git-dir', os.path.join(args.gitdir, '.git'),
     'describe', '--tags', '--long' ],
    shell=True
    ).strip().decode()

vlist = gitver.split('-')
vlist.pop()
commits = vlist.pop()
version = '{}.{}'.format('-'.join(vlist), commits)
logging.info('Git version {}'.format(version))

distdir = os.path.join(args.gitdir, 'dist')
# get packaged version
pkg_version = None
for f in os.listdir(distdir):
    fpath = os.path.join(distdir, f)
    if os.path.isfile(fpath):
        m = re.match(r'machination-client-core-(\d+\.\d+\.\d+)', f)
        if m:
            pkg_version = m.group(1)
            break
logging.info('Packaged version {}'.format(pkg_version))

if version != pkg_version:
    # Make new packages

    # Clean dist
    for f in os.listdir(distdir):
        fpath = os.path.join(distdir, f)
        if os.path.isfile(fpath) and f.startswith('machination-client'):
            logging.info('cleaning pkg {}'.format(f))
            os.remove(fpath)

    # Clean bundles
    for d in os.listdir(args.bundle_dir):
        dpath = os.path.join(args.bundle_dir, d)
        if os.path.isdir(dpath) and d. startswith('machination-client'):
            logging.info('cleaning bundle {}'.format(d))
            shutil.rmtree(dpath)

    # Make new packages
    subprocess.check_call(
        [sys.executable,
         os.path.join(args.gitdir, 'setup.py'),
         bdist_cmd]
        )

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
    logging.debug('testing {} for pkgid'.format(f))
    m = re.match(r'(machination-client-.*)-{}'.format(version), f)
    pkgname = m.group(1)
    logging.info('bundling {} version {}'.format(pkgname, version))
    pkgid = '{}-{}'.format(pkgname, version)
    pkgids.append(pkgid)
    if not os.path.exists(os.path.join(args.bundle_dir, pkgid)):
        os.mkdir(os.path.join(args.bundle_dir, pkgid))
        os.mkdir(os.path.join(args.bundle_dir, pkgid, 'files'))
        shutil.copy(fpath, os.path.join(args.bundle_dir, pkgid, 'files'))

# Construct installed_version.xml
logging.info('constructing iv.xml with bundleDir {}'.format(args.bundle_dir))
iv = etree.Element('iv', bundleDir = args.bundle_dir)
current = etree.Element('installedVersion', version='current')
desired = etree.Element('installedVersion', version='desired')
# desired from pkgids
for pkgid in pkgids:
    logging.info('adding {} to desired'.format(pkgid))
    desired.append(
        etree.Element('machinationFetcherBundle', id = pkgid)
        )
# current from system
# TODO(colin): support other OSes
con = wmi.WMI()
for prod in con.query(
    "select * from Win32_Product where Name like 'Python machination-client%'"
    ):
    logging.info('adding {} to current'.format(prod.Name[7:]))
    current.append(etree.Element('machinationFetcherBundle', id=prod.Name[7:]))
iv.append(current)
iv.append(desired)
# write to file
with open('iv.xml', "w") as ivf:
    ivf.write(etree.tostring(iv, pretty_print=True).decode())

# Only do the update if args.update = 1
if args.update != '1':
    logging.info('No actual update requested: exiting.')
    sys.exit(0)

# invoke self update
args = [
    sys.executable,
    'machination-self-update',
    os.path.join(args.gitdir, 'bin', 'machination-self-update.py'),
    'iv.xml'
    ]
logging.debug(args)
os.execl(*args)
