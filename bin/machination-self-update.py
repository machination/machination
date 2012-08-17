"""Update machination client version"""

from lxml import etree
import sys

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
    # Remove the package
    remove_package(pkgid)

# Remove __machination__
if mw_remove:
    remove_package(pkgid)

# Remove core
if core_remove:
    remove_package(pkgid)

# Add core


# Add others

def pkgname(pkgid):
    """Get package name from bundle id"""
    l = pkgid.split('-')
    l.pop()
    return '-'.join(l)

def abort_update(reason):
    """Uh oh"""
    sys.exit(1)
