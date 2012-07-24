#!/usr/bin/python
"""Join a Machination 2 service"""
import argparse
#import urllib.request
#import http.cookiejar
#from machination.cosign import CosignPasswordMgr, CosignHandler
import machination
from machination import context
from machination.webclient import WebClient
import os
import subprocess
from lxml import etree

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inst_id', nargs='?',
                        help='os_instance id')
    parser.add_argument('--service_id', '-s', nargs='?',
                        help='service id')
    parser.add_argument('--location', '-l', nargs='?',
                        help='parent hc')
    parser.add_argument('--openssl', nargs='?',
                        help='openssl command')
    parser.add_argument('--opensslcfg', nargs='?',
                        help='openssl config file')
    args = parser.parse_args()

    # prefer service_id from args, then first service element from
    # desired_status
    if args.service_id:
        service_id = args.service_id
    else:
        service_id = context.machination_worker_elt.xpath(
            'services/service/@id'
            )[0]

    # Now we have an id, get the appropriate service element
    try:
        service_elt = context.machination_worker_elt.xpath(
            'services/service[@id="{}"]'.format(service_id)
            )[0]
    except IndexError:
        # create an empty one so that the rest of the program will work
        service_elt = etree.Element('service')

    # prefer inst_id from args, then use context.get_id()
    if args.inst_id:
        inst_id = args.inst_id
    else:
        inst_id = context.get_id(service_id)

    # default location
    location = '/system/os_instances'
    if args.location:
        location = args.location

    # defaults for openssl binary and config file
    openssl = 'openssl'
    opensslcfg = None

    # openssl: from args, then from desired_status, then default
    if args.openssl:
        openssl = args.openssl
    else:
        try:
            openssl = context.machination_worker_elt.xpath(
                'openssl/@binary'
                )[0]
        except IndexError:
            pass
    # opensslcfg: from args, then from desired_status, then default
    if args.opensslcfg:
        opensslcfg = args.opensslcfg
    else:
        try:
            opensslcfg = context.machination_worker_elt.xpath(
                'openssl/@config'
                )[0]
        except IndexError:
            pass

    print('inst_id: {}, service_id: {}'.format(inst_id, service_id))
    print('openssl: {}, opensslcfg: {}'.format(openssl, opensslcfg))

    certdir = os.path.join(
        context.conf_dir(),
        'services',
        service_id
        )
    # generate the key
    cmd = []
    cmd.extend([openssl,'genpkey'])
    cmd.extend(['-algorithm','RSA'])
    cmd.extend(['-pkeyopt', 'rsa_keygen_bits:4096'])
    print('genkey: {}'.format(cmd))
    pending_keyfile = os.path.join(certdir, 'pending.key')
    print('Generating new key')
#    key = subprocess.check_output(cmd)
#    with machination.create_secret_file(pending_keyfile,'wb') as f:
#        f.write(key)
    with open(pending_keyfile) as f:
        key = f.read()

    # generate the csr
    cmd = []
    cmd.extend([openssl,'req','-new'])
    if opensslcfg is not None:
        cmd.extend(['-config',opensslcfg])
    cmd.extend(['-key', pending_keyfile])
    # Find the base DN for certs for this service.
    wc = WebClient(service_id, 'person')
    certinfo = wc.call('CertInfo')
    # Fill in any blanks.
    required = ['C','ST','L','O','OU','CN']
    try:
        # Anything not from server comes from desired_status
        defaults = service_elt.xpath('certInfo')[0]
    except IndexError:
        # If there is no element then we need to call get() on something
        defaults = {}
    subject = ''
    for field in required:
        value = certinfo.get(field)
        if value is None:
            value = defaults.get(field)
        while value is None:
            value = input('##{} required: '.format(field))
            if value == '':
                value = None
        print('{}: {}'.format(field, value))
        subject = '{}/{}={}'.format(subject, field, value)
    # now continue building the command
    cmd.extend(['-subj', subject])
    print('Generating certificate request')
    csr = subprocess.check_output(cmd)
    pending_csrfile = os.path.join(certdir, 'pending.csr')
    with machination.create_secret_file(pending_csrfile,'wb') as f:
        f.write(csr)

    path = '{}/os_instance:{}'.format(location, inst_id)
    sysname = platform.system()
    if sysname == 'Windows':
        if 'PROGRAMFILES(X86)' in os.environ:
            bitness = 64
        else:
            bitness = 32
        major = platform.win32_ver()[0]
        minor = platform.win32_ver()[2]
    elif sysname == 'Linux':
        pass
    os_id = wc.call('OsId', sysname, major, minor, bitness)
    # try to create the object
    wc.call('Create', path, {'os_id': os_id})

    exit()

    answer = wc.call("JoinService", csr.decode('utf8'), None, False)
    if isinstance(answer, dict):
        # Didn't get all the way to a cert for some reason

        # currently the only allowed reason is "id exists: are you sure?"
        ans = ''
        while ans.lower() not in ['y', 'n']:
            ans = input('id exists, are you sure [y/N]? ')
        if ans.lower() == 'n':
            print('Aborting service join')
            exit()
        # Try again with force = True
        cert = wc.call("JoinService", csr.decode('utf8'), None, True)
    else:
        cert = answer

    keyfile = os.path.join(certdir, 'myself.key')
    certfile = os.path.join(certdir, 'myself.crt')

    # Remove existing key file.
    try:
        os.remove(keyfile)
    except OSError as e:
        if e.errno == 2:
            pass
    # Replace with new one.
    os.rename(pending_keyfile, keyfile)

    # Remove existing cert file.
    try:
        os.remove(certfile)
    except OSError as e:
        if e.errno == 2:
            pass
    # Create new one.
    with open(certfile, 'wb') as f:
        f.write(cert)
