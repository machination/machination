#!/usr/bin/python

from setuptools import setup, find_packages
from distutils.command.clean import clean
from multiprocessing import Process
import os
import errno
import subprocess
import sys


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
        vlist = version.split('-')
        # Not interested in sha-1.
        vlist.pop()
        commits = vlist.pop()
        version = '{}.{}'.format('-'.join(vlist), commits)
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
    setup(script_name="setup.py", script_args=["clean", "--all"])


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


if __name__ == "__main__":

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
             ['bin/join-service.py',
              'bin/machination-self-update.py',
              'bin/update-to-latest.py']),
            (os.path.join(appdata_dir,'log'),[]),
            (os.path.join(appdata_dir, 'services'),[]),
            ]
    else:
        scripts = []
        scriptargs = []
        data_files = []

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

    # Build each worker package
    basedir = "machination/workers"
    for item in os.listdir(basedir):
        # exceptions
        if item in ('__pycache__'):
            continue
        if os.path.isdir(os.path.join(basedir, item)):
            p = Process(
                target = run_setup,
                args = (
                    "machination-client-worker-" + item,
                    ["machination.workers." + item],
                    ["description.xml"],
                    )
                )
            p.start()
            p.join()
