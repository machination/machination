"""Update machination client version"""

from lxml import etree
import sys
import re

if len(sys.argv) > 1:
    ivtree = etree.parse(sys.argv[1])
else:
    ivtree = etree.parse(sys.stdin)

current = ivtree.xpath('//installedVersion[@version="current"]')[0]
desired = ivtree.xpath('//installedVersion[@version="desired"]')[0]
bundle_dir = ivtree.xpath('/iv/@bundleDir')[0]

# Find adds and removes and nochange.
add = set()
add_names = set()
remove = set()
remove_names = set()
nochange = set()
nochange_names = set()
for bundle in current:
    if desired.xpath('bundle[@id=""]'.format(bundle.get('id'))):
        nochange.add(bundle.get('id'))
        name = pkgname(bundle.get('id'))
        nochange_names.add(name)
        # If a package with the same name (different version) is being
        # added or removed we're in trouble
        if name in add_names | remove_names:
            abort_update('{} with nochange in add or remove'.format(name))
    else:
        remove.add(bundle.get('id'))
        name = pkgname(bundle.get('id'))
        remove_names.add(name)
        if name in nochange_names:
            abort_update('{} with remove also in nochange'.format(name))
for bundle in desired:
    if not current.xpath('bundle[@id=""]'.format(bundle.get('id'))):
        add.add(bundle.get('id'))
        name = pkgname(bundle.get('id'))
        add_names.add(name)
        if name in nochange_names:
            abort_update('{} with add also in nochange'.format(name))

# Remove any non core packages
core_remove = None
mw_remove = None
for pkgid in remove:
    # Skip core, __machination__ worker
    if pkgname(pkgid) == 'machination-client-core':
        core_remove = pkgid
        continue
    if pkgname(pkgid) == 'machination-client-worker-__machination__':
        mw_remove = pkgid
        continue
    # Uninstall the package
    uninstall_package(pkgid)

# Remove __machination__
if mw_remove:
    uninstall_package(pkgid)

# Remove core
if core_remove:
    uninstall_package(pkgid)

# Add core, __machination__
add_mw = None
for pkgid in add:
    if pkgname(pkgid) == 'machination-client-core':
        add.remove(pkgid)
        install_package(pkgid)
    if pkgname(pkgid) == 'machination-client-worker-__machination__':
        add.remove(pkgid)
        add_mw = pkgid
if add_mw:
    install_package(pkgid)

# Add others
for pkgid in add:
    install_package(pkgid)

def pkgname(pkgid):
    """Get package name from bundle id"""
    l = pkgid.split('-')
    l.pop()
    return '-'.join(l)

def abort_update(reason):
    """Uh oh"""
    sys.exit(1)

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

def install_package(pkgid):
    """Install package with id pkgid"""
    pkg_regex = '^{}.*\\.{}$'.format(pkgid, pkg_extension())
    directory = os.path.join(
        bundle_dir,
        pkgid,
        'files'
        )
    
    funcname = 'install_{}'.format(pkg_extension())
    getattr(sys.modules[__name__], funcname)(filename)

def uninstall_package(pkgid):
    """Uninstall package with id pkgid"""
    funcname = 'uninstall_{}'.format(pkg_extension())
    getattr(sys.modules[__name__], funcname)(pkgid)

def install_msi(fname):
    """Install an msi from file"""
    abort_update('install_msi not yet implemented')

def install_deb(fname):
    """Install a deb from file"""
    abort_update('install_deb not yet implemented')

def install_rpm(fname):
    """Install an rpm from file"""
    abort_update('install_rpm not yet implemented')

def uninstall_msi(pkgid):
    """Uninstall an msi"""
    abort_update('uninstall_msi not yet implemented')

def uninstall_deb(pkgid):
    """Uninstall a deb"""
    abort_update('uninstall_deb not yet implemented')

def uninstall_rpm(pkgid):
    """Uninstall an rpm"""
    abort_update('uninstall_rpm not yet implemented')
