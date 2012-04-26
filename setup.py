#!/usr/bin/python

from setuptools import setup, find_packages
from distutils.command.clean import clean
import os
import errno
import subprocess


def git_describe(abbrev=4):
    try:
        return subprocess.check_output(
            ['git', 'describe', '--abbrev=%d' % abbrev]).strip()
    except:
        return None


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

    # If that doesn't work, fall back on the value that's in
    # RELEASE-VERSION.

    # Read in the version that's currently in RELEASE-VERSION.
    release_version = read_release_version()

    if version is None:
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


def run_setup(pkgname, pkglist):

    #Cleanup at end of successful setup
    clean_all()

    # clean_all throws 'build' away, and setup doesn't recreate it!
    try:
        os.mkdir("build")
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    setup(
        name=pkgname,
        version=get_git_version(),
        author="Colin Higgs, Bruce Duncan, Matthew Richardson, Stewart Wilson",
        author_email="machination@see.ed.ac.uk",
        description="The Machination Configuration Management System.",
        license="GPL",
        keywords="configuration management machination",
        url="http://www.github.com/machination/machination",
        packages=pkglist,
        scripts=["machination/service/win32/msi-post-install"],
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Topic :: Utilities",
            "License :: OSI Approved :: GPL License",
            ],
        )


if __name__ == "__main__":

    # Build machination core (without workers or tests)
    run_setup("machination", (find_packages(exclude=["tests",
                                                     "*.workers",
                                                     "*.workers.*",
                                                     "workers.*",
                                                     "workers"])))

    # Build each worker package
    basedir = "machination/workers"
    for item in os.listdir(basedir):
        if os.path.isdir(os.path.join(basedir, item)):
            run_setup("machination-" + item, ["machination.workers." + item])
