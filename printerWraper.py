#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""script wraper for stand alone printer worker"""

from lxml import etree
from machination import context
from machination import xmltools
from machination.workers import printer
import machination
import win32com.client


def WraperMain():

    ### Adding printers
    #chosenPrinters = """
    #<worker id="printer">
    #<wu id='/status/worker[@id="printer"]/printer[@id="al116"]'
    #op='add'>
    #    <printer id="al116">
    #        <basename>al116</basename>
    #        <printer_name>al116</printer_name>
    #        <net_addr>http://cups.see.ed.ac.uk:631/printers/al116</net_addr>
    #        <model>Kyocera FS-3900DN</model>
    #        <driver/>
    #        <inf/>
    #    </printer>
    #</wu>
    #</worker>
    #"""
    #chosenPrinters = """
    #<worker id="printer">
    #<wu id='/status/worker[@id="printer"]/printer[@id="xeroxal"]'
    #op='add'>
    #    <printer id="xeroxal">
    #        <basename>xeroxal</basename>
    #        <printer_name>xeroxal</printer_name>
    #        <net_addr>http://cups.see.ed.ac.uk:631/printers/xeroxal</net_addr>
    #        <model>Xerox WorkCenter 7535 PCL6</model>
    #        <driver>C:\Xerox\WC7545-7556_PCL6_x64_Driver.inf</driver>
    #        <inf>C:\Xerox\WC7545-7556_PCL6_x64_Driver.inf\\x2DNORX.inf</inf>
    #    </printer>
    #</wu>
    #</worker>
    #"""

    ### Removing printers
    chosenPrinters = """
    <worker id="printer">
    <wu id='/status/worker[@id="printer"]/printer[@id="al116"]'
    op='remove'>
        <printer id="al116">
            <basename>al116</basename>
            <printer_name>al116</printer_name>
            <net_addr>http://cups.see.ed.ac.uk:631/printers/al116</net_addr>
            <model>Kyocera FS-3900DN</model>
            <driver/>
            <inf/>
        </printer>
    </wu>
    </worker>
    """



    #found that this xml must have all the tags in comandops 
    #and must have and inf feald of list is out of range
    printerini = machination.workers.printer.Worker()

    wu = etree.fromstring(chosenPrinters)

    printerini.do_work(wu)

if __name__ == "__main__":
    WraperMain()