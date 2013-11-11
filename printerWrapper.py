#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""script wraper for stand alone printer worker"""

from lxml import etree
from machination import context
from machination import xmltools
from machination.workers import printer
import machination
import win32com.client
import sys

def WraperMain(file):

    ### Adding printers
    with open(file) as chosenPrinter:
             printer_wu = chosenPrinter.read()
             print(printer_wu)
             printerini = machination.workers.printer.Worker()
             wu = etree.fromstring(printer_wu)
             printerini.do_work(wu)

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        WraperMain(arg)
