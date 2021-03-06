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
import io
import subprocess
from lxml import etree
import re
import logging
import sys

logging.basicConfig(level=logging.DEBUG)

def get_authen_info():
    '''Prompt for information in authentication type'''
    valid_atypes = {
        'basic': [],
        'cosign': ['cosignLoginPage'],
        'cert': [],
        'debug': ['username']
        }
    atype = input(
        'Athentication type ({}): '.format(tuple(valid_atypes.keys()))
        )
    while atype not in valid_atypes:
        atype = input(
            'Athentication type ({}): '.format(tuple(valid_atypes.keys()))
            )
    ret = {
        'type': atype
        }
    for extra in valid_atypes[atype]:
        value = input('  {}: '.format(extra))
        ret[extra] = value

    return ret

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', '-u',
                        default='http://localhost/machination/hierarchy',
                        help='hierarchy url')
    parser.add_argument('--inst_id', '-i', required=True,
                        help='os_instance id')
    parser.add_argument('--entitytype', '-t',
                        default='person',
                        help='type of entity to authenticate as')
    parser.add_argument(
        '--authtype', '-a',
        help='authentication type (basic, cert, cosign, ...)'
        )
    parser.add_argument(
        '--cred', '-c', action='append',
        help='credentials entry separated by "=" (e.g. name=foo)'
        )
    parser.add_argument('--location', '-l', default='/system/os_instances',
                        help='parent hc')
    parser.add_argument('--service_id', '-s',
                        help='service id')
    parser.add_argument('--openssl',
                        help='openssl command')
    parser.add_argument('--opensslcfg',
                        help='openssl config file')
    parser.add_argument('--certbits',
                        help='No of bits for certificate cipher')
    parser.add_argument('--rejoin', default='',
                        help='Rejoin service if os instance exists (y or n)')
    parser.add_argument('--new_osid', action='store_true',
                        help="Create new os_id if one doesn't exist")
    args = parser.parse_args()

#    print(args)
#    sys.exit()

    if args.cred:
        cred = dict(s.split('=',1) for s in args.cred)
    else:
        cred = {}

    try:
        services_elt = context.machination_worker_elt.xpath('services')[0]
    except IndexError:
        service_elt = etree.Element('services')

    # We need a hierarchy url to get started
    hierarchy = args.url
    service_elt = None
    # If there isn't one, we should look in desired_status
    if not hierarchy:
        logging.info('No hierarchy url specified')
        if args.service_id:
            logging.info('  Looking for service[{}].'.format(args.service_id))
            try:
                service_elt = services_elt.xpath(
                    'service[@id="{}"]'.format(args.service_id)
                    )[0]
                logging.info('  Found one.')
            except IndexError:
                logging.info("  Didn't find one.")
            if service_elt is not None:
                try:
                    hierarchy = service_elt.xpath('hierarchy/@id')[0]
                except IndexError:
                    pass
    # If we still haven't found one, ask the user
    if not hierarchy:
        hierarchy = input('hierarchy url: ')

    pubwc = WebClient(hierarchy, 'public', 'os_instance')
    if service_elt is None:
        service_elt = etree.fromstring(pubwc.call('ServiceInfo'))
        service_elt.set('fromServiceInfo', '1')

    # Get the service id
    service_id = service_elt.get('id')

    # Make sure there is an authentication type for person objects
    if not service_elt.xpath('authentication[@id="person"]'):
        kwargs = get_authen_info()
        service_elt.append(
            etree.Element('authentication', **kwargs)
            )

    # prefer inst_id from args, then use context.get_id()
    if args.inst_id:
        inst_id = args.inst_id
    else:
        inst_id = context.get_id(service_id)
    # we need an inst_id
    while inst_id is None:
        inst_id = input('instance id required: ')
        if inst_id == '':
            inst_id = None

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

    service_dir = os.path.join(
        context.conf_dir(),
        'services',
        service_id
        )
    # make sure service_dir exists
    if not os.path.exists(service_dir):
        os.makedirs(service_dir)
    # generate the key
    cmd = []
    cmd.extend([openssl,'genpkey'])
    cmd.extend(['-algorithm','RSA'])
    cmd.extend(['-pkeyopt', 'rsa_keygen_bits:{}'.format(certbits)])
    print('genkey: {}'.format(cmd))
    pending_keyfile = os.path.join(service_dir, 'pending.key')
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
    print(etree.tostring(service_elt))
    wc = WebClient(args.url, args.authtype, args.entitytype, credentials=cred)
    basedn = wc.call('CertInfo').get('basedn_string_slash')
    cn = 'os_instance:{}'.format(inst_id)
    subject = '{}/CN={}'.format(basedn,cn)

    # now continue building the command
    cmd.extend(['-subj', subject])
    print('Generating certificate request')
    csr = subprocess.check_output(cmd)
    pending_csrfile = os.path.join(service_dir, 'pending.csr')
    with machination.create_secret_file(pending_csrfile,'wb') as f:
        f.write(csr)

    path = '{}/os_instance:{}'.format(location, inst_id)
    os_id = wc.call('OsId', *machination.utils.os_info())
    if os_id is None:
        if args.new_osid:
            # Try to make a new os_id
            wc.call('AddValidOs', *machination.utils.os_info())
            os_id = wc.call('OsId', *machination.utils.os_info())
        else:
            raise Exception("Could not find os_id for {}".format(" ".join([str(x) for x in machination.utils.os_info()])))
    # try to create the object
    try:
        wc.call('Create', path, {'os_id': os_id})
    except Exception as e:
        if re.search(
            r'Cannot create os_instance {}'.format(inst_id),
            e.args[0]
            ):
            # inst_id already exists and is in the location we asked for
            print('Object os_instance:{} already exists'.format(inst_id))
        elif re.search(r'ERROR:\s+ duplicate key value', e.args[0]):
            # inst_id already exists somewhere else
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
            ans = args.rejoin
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

    keyfile = os.path.join(service_dir, 'myself.key')
    certfile = os.path.join(service_dir, 'myself.crt')

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

    # Update mid.txt
    with open(os.path.join(service_dir, 'mid.txt'), 'w') as f:
        f.write(inst_id)

    # Add service to desired_status if we had to query the server for
    # it.
    if service_elt.get('fromServiceInfo') == "1":
        logging.info('Got service info from service url, adding to desired_status')
        ds = context.desired_status
        if ds.getroot().get('autoconstructed'):
            del(ds.getroot().attrib['autoconstructed'])
        try:
            svcs_elt = context.machination_worker_elt.xpath('services')[0]
        except IndexError:
            svcs_elt = etree.Element('services')
            context.machination_worker_elt.append(svcs_elt)
        svcs_elt.append(service_elt)
        # Save to file
        ds_file = os.path.join(context.status_dir(), 'desired-status.xml')
        logging.info('Saving desired status to {}'.format(ds_file))
        with open(ds_file, 'w') as f:
            f.write(etree.tostring(ds, pretty_print = True).decode())
