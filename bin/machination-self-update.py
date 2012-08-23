#!/usr/bin/python
"""Update machination client version"""

from lxml import etree
import sys
import re
import platform
import logging
import os
import pprint
import copy
import errno

logging.basicConfig(level=logging.DEBUG)

core = {
    'machination-client-core',
    }
corew = {
    'machination-client-worker-__machination__',
    'machination-client-worker-fetcher'
    }
allcore = core | corew

def pkgname(pkgid):
    """Get package name from bundle id"""
    l = pkgid.split('-')
    l.pop()
    return '-'.join(l)

def pkg_extension():
    if platform.system() == 'Windows':
        return 'msi'
    elif platform.system() == 'Linux':
        dist = platform.dist()[0]
        if dist == 'Ubuntu':
            return 'deb'
        elif dist == 'redhat':
            return 'rpm'
        else:
            abort_update(
                'pkg_extension: unknown Linux distro "{}"'.format(dist)
                )
    else:
        abort_update(
            'pkg_extension: unknown system "{}"'.format(platform.system())
            )

def pkg_file(pkgid):
    """Find the package file for pkgid"""
    pkg_re = re.compile('^{}.*\\.{}$'.format(pkgid, pkg_extension()))
    directory = os.path.join(
        bundle_dir,
        pkgid,
        'files'
        )
    try:
        os.listdir(directory)
    except:
        raise IOError(
            errno.ENOENT,
            'bundle dir not found for {}'.format(pkgid)
            )
    filename = None
    # Find the package file
    for f in os.listdir(directory):
        if os.path.isdir(f):
            continue
        if pkg_re.search(f):
            filename = os.path.join(directory, f)
            break
    if not filename:
        raise IOError(
            errno.ENOENT,
            'package file not found for {}'.format(pkgid)
            )

    return filename

def install_package(pkgid):
    """Install package with id pkgid"""
    logging.info('installing {}'.format(pkgid))

    funcname = 'install_{}'.format(pkg_extension())
    try:
        filename = pkg_file(pkgid)
    except IOError as e:
        logging.error(e)
        return
    logging.info('installing {} with {}'.format(filename, funcname))
    getattr(sys.modules[__name__], funcname)(filename)

def uninstall_package(pkgid):
    """Uninstall package with id pkgid"""
    logging.info('uninstalling {}'.format(pkgid))
    funcname = 'uninstall_{}'.format(pkg_extension())
    getattr(sys.modules[__name__], funcname)(pkgid)

def ug_uninstall_package(ids):
    """Uninstall ids[0] only if package file can be found for ids[1]"""
    try:
        pkg_file(ids[1])
    except IOError as e:
        logging.error(e)
        logging.info('skipping upgrade uninstall of {}'.format(ids[0]))
    else:
        logging.info('upgrade uninstall {}'.format(ids[0]))
        uninstall_package(ids[0])

def install_msi(fname):
    """Install an msi from file"""
    results = wmic.Win32_Product.Install(
        True,
        '',
        fname,
        )
    if results[0] != 0:
        # Dont' abort - we want to continue and try to install as much
        # as possible.
        #
        # Do warn though
        logging.warning('MSI install of {} reported {}'.format(fname, results))

def install_deb(fname):
    """Install a deb from file"""
    abort_update('install_deb not yet implemented')

def install_rpm(fname):
    """Install an rpm from file"""
    abort_update('install_rpm not yet implemented')

def uninstall_msi(pkgid):
    """Uninstall an msi"""
    for prod in wmic.Win32_Product(name='Python {}'.format(pkgid)):
        try:
            results = prod.Uninstall()
        except Exception as e:
            abort_update('Error uninstalling {}:\n{}'.format(pkgid, e))
        if results[0] != 0:
            abort_update('Error uninstalling {}, error no. {}'.format(pkgid, results[0]))

def uninstall_deb(pkgid):
    """Uninstall a deb"""
    abort_update('uninstall_deb not yet implemented')

def uninstall_rpm(pkgid):
    """Uninstall an rpm"""
    abort_update('uninstall_rpm not yet implemented')

def abort_update(msg):
    """Uh oh"""
    logging.warning(msg)
    sys.exit(1)

if platform.system() == 'Windows':
    import wmi
    wmic = wmi.WMI()

if len(sys.argv) > 1:
    ivtree = etree.parse(sys.argv[1])
else:
    ivtree = etree.parse(sys.stdin)

current = ivtree.xpath('//installedVersion[@version="current"]')[0]
desired = ivtree.xpath('//installedVersion[@version="desired"]')[0]
bundle_dir = ivtree.xpath('/iv/@bundleDir')[0]

# Find adds, removes and nochanges.
add = set()
add_names = set()
remove = set()
remove_names = set()
update = {}
update_names = set()
nochange = set()
nochange_names = set()
for bundle in current:
    if desired.xpath(
        'machinationFetcherBundle[@id="{}"]'.format(bundle.get('id'))
        ):
        logging.debug('adding {} to nochange'.format(bundle.get('id')))
        nochange.add(bundle.get('id'))
        name = pkgname(bundle.get('id'))
        nochange_names.add(name)
        # If a package with the same name (different version) is being
        # added or removed we're in trouble
        if name in add_names | remove_names:
            abort_update('{} with nochange already in add or remove'.format(name))
    else:
        remove.add(bundle.get('id'))
        name = pkgname(bundle.get('id'))
        logging.debug('adding name {} to remove_names'.format(name))
        remove_names.add(name)
        if name in nochange_names:
            abort_update('{} with remove also in nochange'.format(name))
for bundle in desired:
    if not current.xpath('machinationFetcherBundle[@id="{}"]'.format(bundle.get('id'))):
        name = pkgname(bundle.get('id'))
        if name in nochange_names:
            abort_update('{} with add also in nochange'.format(name))
        if name in remove_names:
            # really an update
            remove_names.remove(name)
            oldid = None
            for rpid in copy.copy(remove):
                if(rpid.startswith(name)):
                    oldid = rpid
                    break
            remove.remove(oldid)
            update[name] = [oldid, bundle.get('id')]
            update_names.add(name)
        else:
            add.add(bundle.get('id'))
            add_names.add(name)

logging.info('Things to do:')
logging.info('Nothing:')
logging.info(pprint.pprint(nochange))
logging.info('Remove:')
logging.info(pprint.pprint(remove))
logging.info('Add:')
logging.info(pprint.pprint(add))
logging.info('Update:')
logging.info(pprint.pprint(update))

# Removes
for pkgid in remove:
    name = pkgname(pkgid)
    if name in allcore:
        logging.warning('Asked to remove {} in never_remove - skipping'.format(pkgid))
        continue
    uninstall_package(pkgid)

# Update removes
ucore = set()
ucorew = set()
uotherw = set()
# uninstall non core_set, remember others
for name, ids in update.items():
    if name in core:
        ucore.add(name)
    elif name in corew:
        ucorew.add(name)
    else:
        uotherw.add(name)
        ug_uninstall_package(ids)
# uninstall core workers
for name in ucorew:
    logging.info(
        'uninstalling core worker {} for upgrade'.format(update[name][0]))
    ug_uninstall_package(update[name])
for name in ucore:
    logging.info(
        'uninstalling core {} for upgrade'.format(update[name][0]))
    ug_uninstall_package(update[name])

# Update adds
for name in ucore:
    pkgid = update[name][1]
    logging.info('installing core {} as upgrade'.format(pkgid))
    install_package(pkgid)
for name in ucorew:
    pkgid = update[name][1]
    logging.info('installing core worker {} as upgrade'.format(pkgid))
    install_package(pkgid)
for name in uotherw:
    pkgid = update[name][1]
    logging.info('installing non core {} as upgrade'.format(pkgid))
    install_package(pkgid)

# Adds
for pkgid in add:
    logging.info('installing non core {} as add'.format(pkgid))
    install_package(pkgid)
