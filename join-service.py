#!/usr/bin/python
"""Join a Machination 2 service"""
import argparse
#import urllib.request
#import http.cookiejar
#from machination.cosign import CosignPasswordMgr, CosignHandler
from machination import context
from machination.webclient import WebClient

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('os_id', nargs='?',
                        help='os_instance id')
    parser.add_argument('--service_id', '-s', nargs='?',
                        help='service id')
    parser.add_argument('--openssl', nargs='?',
                        help='openssl command')
    parser.add_argument('--opensslcfg', nargs='?',
                        help='openssl config file')
    args = parser.parse_args()

    if args.service_id:
        service_id = args.service_id
    else:
        service_id = context.desired_status.xpath(
            '/status/worker[@id="__machination__"]/services/service/@id'
            )[0]
    if args.os_id:
        os_id = args.os_id
    else:
        os_id = context.get_id(service_id)

    openssl = 'openssl'
    opensslcfg = None
    try:
        openssl = context.machination_worker_elt.xpath(
            'openssl/@binary'
            )[0]
    except IndexError:
        pass

    print('os_id: {}, service_id: {}'.format(os_id, service_id))
    exit()
    wc = WebClient(service_id, 'person')
    wc.call("JoinService", csr, location)
