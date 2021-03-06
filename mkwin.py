#!/usr/bin/python

from setuptools import setup, find_packages
from distutils.command.clean import clean
from multiprocessing import Process
import logging
import os
import errno
import subprocess
import sys
import msilib
import re
import glob
from lxml import etree

logging.basicConfig(level=logging.DEBUG)

def git_describe():
    return subprocess.check_output(
        ['git', 'describe', '--tags', '--long' ],
        shell=True
        ).strip().decode()

def read_release_version():

    try:
        with open("RELEASE-VERSION", "r") as f:
            version = f.readlines()[0]
            return version.strip()
    except:
        return None


def write_release_version(version):
    f = open("RELEASE-VERSION", "w")
    f.write("%s\n" % version)
    f.close()


def get_git_version():
    # First try to get the current version using "git describe".

    version = git_describe()
    release_version = read_release_version()
    if version:
        # Get the release tag and number of commits away from that
        # release from git.
        [gtag, gcommits, ghash] = version.split('-')

        # The tag should be in the form 1.2.3 (three numbers separated
        # by '.'): major.minor.bugfix
        gversions = gtag.split(".")

        # Don't have to specifiy all three numbers in the git
        # tag. We'd better add any missing ones back in.
        while len(gversions) < 3:
            gversions.append("0")

        # The following looks insane, but it is a workaround to the
        # fact that we want a four number version
        # (major.minor.bugfix.commits) when in a debugging cycle
        # whilst the MSI package format only allows three. On the
        # other hand the last number in the MSI version format can be
        # from 0-65535 (two bytes), so we munge our last two numbers
        # into one by restricting them to 0-255 (one byte) each.
        gupdate = gversions.pop()
        versions = gversions
        versions.append(str(int(gupdate)*256 + int(gcommits)))
        version = ".".join(versions)
    else:
        # If that doesn't work, fall back on the value that's in
        # RELEASE-VERSION.
        version = release_version

    # If we still don't have anything, that's an error.
    if version is None:
        raise ValueError("Cannot find the version number!")

    # If the current version is different from what's in the
    # RELEASE-VERSION file, update the file to be current.
    if version != release_version:
        write_release_version(version)

    return version


def clean_all():
    """Call setup.py clean --all"""

    # HACK!
    setup(script_name="mkwin.py", script_args=["clean", "--all"])
    for f in glob.iglob('build/*.wsx'):
        os.unlink(f)
    for f in glob.iglob('build/*.wixobj'):
        os.unlink(f)

def run_setup(pkgname, pkglist, datalist=[], scriptlist=[],
              scriptargs=sys.argv[1:], data_files=[]):

    #Cleanup at end of successful setup
    clean_all()

    # clean_all throws 'build' away, and setup doesn't recreate it!
    try:
        os.mkdir("build")
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    setup(
        script_args=scriptargs,
        name=pkgname,
        version=get_git_version(),
        author="Colin Higgs, Bruce Duncan, Matthew Richardson, Stewart Wilson",
        author_email="machination@see.ed.ac.uk",
        description="The Machination Configuration Management System.",
        license="GPL",
        keywords="configuration management machination",
        url="http://www.github.com/machination/machination",
        packages=pkglist,
        package_data={pkgname: datalist},
        scripts=scriptlist,
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Topic :: Utilities",
            "License :: OSI Approved :: GPL License",
            ],
        data_files=data_files,
        )

def make_worker_msi(basedir, wname):

    logging.info('making msi for {} in {}'.format(wname, basedir))
    wixdir = r'c:\Program Files (x86)\Windows Installer XML v3.6\bin'
    candle = os.path.join(wixdir, 'candle.exe')
    light = os.path.join(wixdir, 'light.exe')
    version = get_git_version()
    pname = 'machination-client-worker-' + wname
    fullname = 'Python {}-{}'.format(pname, version)
    out = 'build\\{}-{}.wsx'.format(pname, version)
    wsx = etree.parse('packaging/machination-client-worker-template.xml')
    top = wsx.getroot()

    # Change 'macros'
    for elt in top.iter(tag=etree.Element):
        for att in elt.attrib:
            if elt.get(att) == 'REP-WORKERNAME': elt.set(att, wname)
            if elt.get(att) == 'REP-FULLNAME': elt.set(att, fullname)
            if elt.get(att) == 'REP-VERSION': elt.set(att, version)
            if elt.get(att) == 'REP-GUID': elt.set(att, msilib.gen_uuid())

    # Add files
    nsmap = {'w': 'http://schemas.microsoft.com/wix/2006/wi'}
    wdref_elt = top.xpath('//w:DirectoryRef[@Id="THEWORKERDIR"]', namespaces = nsmap)[0]
    feature_elt = top.xpath('//w:Feature[@Id="MachWorker"]', namespaces = nsmap)[0]
    wdir = basedir + '\\' + wname
    for thing in os.listdir(wdir):
        # exceptions
        if thing in ('__pychache__'):
            continue
        if os.path.isdir(wdir + '\\' + thing):
            logging.warning('Found a directory: ' + thing)
        else:
            comp = etree.Element('Component', Id=make_id(thing), Guid=msilib.gen_uuid())
            comp.append(
                etree.Element(
                    'File',
                    Id=make_id(thing),
                    Source='{}\\{}'.format(wdir, thing)
                    )
                )
            wdref_elt.append(comp)
            feature_elt.append(etree.Element('ComponentRef', Id=make_id(thing)))

    # Write the source file out
    logging.info('Creating ' + out)
    with open(out, "w") as f:
        f.write(etree.tostring(wsx).decode())

    # compile
    subprocess.check_call(
        [candle,
         '-arch', 'x64',
         '-out', 'build\\{}-{}.wixobj'.format(pname, version),
         'build\\{}-{}.wsx'.format(pname, version)]
        )
    # link
    subprocess.check_call(
        [light,
         '-out', 'dist\\{}-{}.x64.msi'.format(pname, version),
         'build\\{}-{}.wixobj'.format(pname, version)]
        )
    # remove temporary file
    os.unlink('dist\\{}-{}.x64.wixpdb'.format(pname, version))

def make_id(text):
    return re.sub(r'[^0-9A-Za-z.]', '_', text)


if __name__ == "__main__":

    # Build each worker package
    basedir = "machination\\workers"
    for item in os.listdir(basedir):
        # exceptions
        if item in ('__pycache__', '__init__.py'):
            continue
        if os.path.isdir(os.path.join(basedir, item)):
            make_worker_msi(basedir, item)

    if len(sys.argv) > 1 and sys.argv[1] == 'bdist_msi':
        scriptdir = "machination/service/win32/"
        scriptfile = "msi-post-install"
        scripts = [scriptdir + scriptfile]

        # Append an install-script to bdist_msi options
        appdata_dir = os.path.join(
            os.environ.get('ALLUSERSPROFILE','C:\\ProgramData'),
            'Machination')
        prog_dir = os.path.join(
            os.environ.get('PROGRAMFILES','C:\\Program Files'),
            'Machination')
        scriptargs = [''.join(sys.argv[1:]), '--install-script', scriptfile]
        data_files = [
            (os.path.join(appdata_dir,'conf'),[]),
            (os.path.join(appdata_dir, 'status'),[]),
            (os.path.join(appdata_dir,'cache'),[]),
            (os.path.join(prog_dir,'bin'),
             ['bin\\join-service.py',
              'bin\\machination-self-update.py',
              'bin\\update-to-latest.py']),
            (os.path.join(appdata_dir,'log'),[]),
            (os.path.join(appdata_dir, 'services'),[]),
            ]
    else:
        scripts = []
        scriptargs = []
        data_files = []

    # Build core extras
    wixdir = r'c:\Program Files (x86)\Windows Installer XML v3.6\bin'
    candle = os.path.join(wixdir, 'candle.exe')
    light = os.path.join(wixdir, 'light.exe')
    version = get_git_version()
    name = 'machination-client-core-extras'
    # Keep the MSI name in the same format as bdist_msi
    fullname = 'Python {}-{}'.format(name, version)
    out = 'build\\{}-{}.wsx'.format(name, version)
    # Parse template and change REP-* to something appropriate
    wsx = etree.parse('packaging/{}-template.xml'.format(name))
    top = wsx.getroot()
    for elt in top.iter(tag=etree.Element):
        for att in elt.attrib:
            if elt.get(att) == 'REP-FULLNAME': elt.set(att, fullname)
            if elt.get(att) == 'REP-VERSION': elt.set(att, version)
            if elt.get(att) == 'REP-GUID': elt.set(att, msilib.gen_uuid())
    # Write a .wsx files for candle to process
    with open(out, "w") as f:
        f.write(etree.tostring(wsx).decode())
    subprocess.check_call(
        [candle,
         '-arch', 'x64',
         '-out', 'build\\{}-{}.wixobj'.format(name, version),
         'build\\{}-{}.wsx'.format(name, version)]
        )
    subprocess.check_call(
        [light,
         '-out', 'dist\\{}-{}.x64.msi'.format(name, version),
         'build\\{}-{}.wixobj'.format(name, version)]
        )
    os.unlink('dist/{}-{}.x64.wixpdb'.format(name, version))

    # Build machination core (without workers or tests)
    core_pkgs = find_packages(
        exclude=["tests",
#                 "*.workers",
                 "*.workers.*",
                 "workers.*",
                 "workers"]
        )
#    core_pkgs.append('machination.workers')

    p = Process(
        target = run_setup,
        args = (
            "machination-client-core",
            core_pkgs,
            ["desired-status.xml"],
            scripts,
            scriptargs,
            data_files
            )
        )
    p.start()
    p.join()

