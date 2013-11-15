#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""script wrapper for stand alone printer worker"""
import sys
from lxml import etree
from machination import context
from machination import xmltools
from machination.workers import printer
import machination
import win32com.client
import argparse
import io

def WrapperMain(wufile, desired_status):
    context.desired_status = desired_status

    ### Adding printers
    wus = etree.parse(wufile).getroot()
#    print(etree.tostring(wus))
    worker = machination.workers.printer.Worker()
    worker.do_work(wus)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--desired', '-d', nargs='?',
        help='desired status file'
        )
    parser.add_argument(
        'wufiles', nargs='+'
        )
    args = parser.parse_args()

    try:
        desired_status = etree.parse(args.desired)
        print("got desired from {}".format(args.desired))
    except:
        print("No desired file, using empty desired status")
        desired_status = etree.parse(
            io.StringIO('<status/>')
            )

    for wufile in args.wufiles:
        WrapperMain(wufile, desired_status)
