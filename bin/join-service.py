#!/usr/bin/python
"""Join a Machination 2 service"""
import argparse
#import urllib.request
#import http.cookiejar
#from machination.cosign import CosignPasswordMgr, CosignHandler
import machination
import machination.utils
from machination import context
from machination.webclient import WebClient
import os
import subprocess
from lxml import etree
import re

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
    parser.add_argument('--certbits', nargs='?',
                        help='No of bits for certificate cipher')
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

    certbits = 4096
    if args.certbits:
        certbits = args.certbits

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
    cmd.extend(['-pkeyopt', 'rsa_keygen_bits:{}'.format(certbits)])
    print('genkey: {}'.format(cmd))
    pending_keyfile = os.path.join(certdir, 'pending.key')
    print('Generating new key')
    key = subprocess.check_output(cmd)
    with machination.create_secret_file(pending_keyfile,'wb') as f:
        f.write(key)
#    with open(pending_keyfile) as f:
#        key = f.read()

    # generate the csr
    cmd = []
    cmd.extend([openssl,'req','-new'])
    if opensslcfg is not None:
        cmd.extend(['-config',opensslcfg])
    cmd.extend(['-key', pending_keyfile])
    # Find the base DN for certs for this service.
    wc = WebClient(service_id, 'person')
    dnform = wc.call('CertInfo').get('dnform', {})
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
        value = dnform.get(field)
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
    os_id = wc.call('OsId', *machination.utils.os_info())
    # try to create the object
    try:
        wc.call('Create', path, {'os_id': os_id})
    except Exception as e:
        if(re.search(r'ERROR:\s+ duplicate key value', e.args[0])):
            print('Object os_instance:{} already exists'.format(inst_id))
        else:
            raise(e)

    # try to create a new cert
    try:
        cert = wc.call("SignIdentityCert", csr.decode('utf8'), 0)
    except Exception as e:
        # Didn't get all the way to a cert for some reason
        if(re.search(r'A valid certificate for', e.args[0])):
            # Currently the only allowed reason is cert exists.
            ans = ''
            while ans.lower() not in ['y', 'n']:
                ans = input('certificate for {} exists, are you sure [y/N]? '.format(inst_id))
                if ans == '':
                    ans = 'n'
                if ans.lower() == 'n':
                    print('Aborting service join')
                    exit()
            # Try again with force = True
            cert = wc.call("SignIdentityCert", csr.decode('utf8'), 1)
        else:
            raise(e)

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
        f.write(cert.encode('utf8'))
