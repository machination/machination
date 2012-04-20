#!/usr/bin/python

from setuptools import setup, find_packages
from distutils.command.clean import clean
import os


def clean_all():
    """Call setup.py clean --all"""

    # HACK!
    setup(script_name = "setup.py", script_args = ["clean", "--all"])


def run_setup(pkgname, pkglist):

    print
    print "PACKAGING: " + pkgname
    print

    # clean_all throws this away, and setup doesn't recreate it!
    os.mkdir("build")

    setup(
        name = pkgname,
        version = "0.0.1",
        author = "Colin Higgs, Bruce Duncan, Matthew Richardson, Stewart Wilson",
        author_email = "machination@see.ed.ac.uk",
        description = ("The Machination Configuration Management System."),
        license = "GPL",
        keywords = "configuration management machination",
        url = "http://www.github.com/machination/machination",
        packages = pkglist,
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Topic :: Utilities",
            "License :: OSI Approved :: GPL License",
            ],
        )

    #Cleanup at end of successful setup
    clean_all()


if __name__ == "__main__":

    # Cleanup before we begin

    clean_all()

    # Build machination core (without workers or tests)
    run_setup("machination", (find_packages(exclude=["tests",
                                                     "*.workers",
                                                     "*.workers.*",
                                                     "workers.*",
                                                     "workers"])[1:]))

    # Build each worker package
    basedir = "machination/workers"
    for item in os.listdir(basedir):
        if os.path.isdir(os.path.join(basedir, item)):
            run_setup("machination-" + item, ["machination.workers." + item])
