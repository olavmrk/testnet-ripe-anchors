#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import copy
import json
import os
import random
import requests
import sys
import time
import threading

def get(url, **kwargs):
    r = requests.get(url, headers={'User-Agent': 'testnet-ripe-anchors.py'}, **kwargs)
    r.raise_for_status()
    return json.loads(r.content)

class Anchor(object):

    # Our ID
    id = None

    # IPv4 address
    address_v4 = None

    # IPv6 address
    address_v6 = None

    def __init__(self, data):
        self.id = data['id']
        self.address_v4 = data['address_v4']
        self.address_v6 = data['address_v6']

    @property
    def init_data(self):
        data = {
            'id': self.id,
            'address_v4': self.address_v4,
            'address_v6': self.address_v6,
        }
        return data

    def __repr__(self):
        return 'Anchor(' + repr(self.init_data) + ')'

class AnchorCache(object):

    # The length of time we want to cache data.
    _CACHE_LENGTH = 3600

    # Our cache file.
    _cache_file = None

    # Whether we have tried to load our cache file.
    _cache_loaded = False

    # Our anchors
    _anchors = None

    # When our anchors list was fetched
    _anchors_time = None

    def __init__(self, cache_file):
        self._cache_file = cache_file

    def _load(self):
        with open(self._cache_file) as fh:
            data = json.load(fh)

        self._anchors = [ Anchor(a) for a in data['anchors'] ]
        self._anchors_time = data['time']

        current_time = time.time()
        if self._anchors_time > current_time:
            # Anchors from the future.
            # Adjust the time so that they are expired. That way
            # they should be replaced with a fresh copy.
            self._anchors_time = current_time - AnchorCache._CACHE_LENGTH

    def _maybe_load_cache(self):
        if self._cache_loaded:
            return # Cache already loaded.
        try:
            self._load()
        except:
            pass # Ignore load errors -- we will just fetch it from the API instead.
        self._cache_loaded = True

    @staticmethod
    def _fetch_anchors():
        ret = []
        url = 'https://atlas.ripe.net/api/v1/probe/?is_anchor=true&status=1'
        while url:
            data = get(url)
            ret.extend([ Anchor(a) for a in data['objects'] ])
            url = data['meta']['next']
            if url:
                url = 'https://atlas.ripe.net' + url
        return ret

    def _write_cache(self):
        data = {
            'time': self._anchors_time,
            'anchors': [ a.init_data for a in self._anchors ],
        }
        new_file = self._cache_file + '.new'
        with open(new_file, 'w') as fh:
            json.dump(data, fh, indent=4)
            fh.write('\n')
        os.rename(new_file, self._cache_file)

    def _refresh(self):
        self._anchors_time = time.time()
        self._anchors = AnchorCache._fetch_anchors()
        self._write_cache()

    @property
    def anchors(self):
        # Load the cache if we haven't before.
        self._maybe_load_cache()

        if not self._anchors:
            # We don't have any anchors from cache. Fetch some.
            self._refresh()

        if self._anchors_time < time.time() - AnchorCache._CACHE_LENGTH:
            # We have anchors, but the cache is expired. Try to refresh it.
            try:
                self._refresh()
            except:
                pass # Use old data if unable to refresh.

        return self._anchors


class Tester(object):

    # Maximum number of parallell threads.
    _MAX_THREADS = 20

    # Our semaphore, used to limit active threads.
    _limiter = None

    # The result of our tests
    _results = None

    # The lock for the result data
    _results_lock = None

    def __init__(self):
        self._limiter = threading.Semaphore(Tester._MAX_THREADS)
        self._results = {}
        self._results_lock = threading.Lock()

    @staticmethod
    def _test_address(address):
        url = 'http://' + address + '/'
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            return True
        except:
            return False

    def run_test(self, address):

        def _test_function():
            result = Tester._test_address(address)
            with self._results_lock:
                self._results[address] = result
            self._limiter.release()

        self._limiter.acquire()
        t = threading.Thread(target=_test_function)
        t.start()

    def _flush_work(self):
        for i in range(0, Tester._MAX_THREADS):
            self._limiter.acquire()
        for i in range(0, Tester._MAX_THREADS):
            self._limiter.release()

    @property
    def results(self):
        self._flush_work()
        with self._results_lock:
            ret = copy.deepcopy(self._results)
        return ret

def parse_args():
    formats = (
        'count',
        'count_total',
        'percent',
        'verbose',
    )
    def num_or_percent(value):
        if value.isdigit():
            # A simple integer, which sets a count.
            return int(value)
        elif len(value) > 1 and value[-1] == '%' and value[:-1].isdigit():
            # A percentage.
            value = int(value[:-1])
            if value > 100:
                raise argparse.ArgumentTypeError('Cannot specify more than 100%.')
            return value / 100.0
        else:
            raise argparse.ArgumentTypeError('Must be an integer or a percentage.')

    parser = argparse.ArgumentParser(description='Test network connectivity')
    parser.add_argument('--all', action='store_true', help='Test against all available targets')
    parser.add_argument('--count', type=num_or_percent, help='Number of targets to test against')
    parser.add_argument('--fail-threshold', type=num_or_percent, help='Failure threshold')
    parser.add_argument('--ipv4', action='store_true', dest='no_ipv6', help='Test only IPv4 targets')
    parser.add_argument('--ipv6', action='store_true', dest='no_ipv4', help='Test only IPv6 targets')
    parser.add_argument('--output', default='verbose', choices=formats, help='Output format')

    args = parser.parse_args()
    if args.all and args.count is not None:
        print('Cannot specify both --all and --count.', file=sys.stderr)
        sys.exit(1)
    if args.no_ipv4 and args.no_ipv6:
        print('Cannot specify both --ipv4 and --ipv6.', file=sys.stderr)
        sys.exit(1)
    return args

def main():

    args = parse_args()

    anchor_cache = AnchorCache('/tmp/testnet-ripe-anchors-cache.json')
    anchors = anchor_cache.anchors

    targets = []
    for a in anchors:
        if a.address_v4 and not args.no_ipv4:
            targets.append(a.address_v4)
        if a.address_v6 and not args.no_ipv6:
            targets.append('[' + a.address_v6 + ']')

    if args.all:
        count = len(targets)
    elif isinstance(args.count, float):
        count = int(args.count * len(targets))
    elif args.count is not None:
        count = args.count
        available = len(targets)
        if count > available:
            print('Requested {count} targets, but only {available} available.'.format(count=count, available=available), file=sys.stderr)
            sys.exit(1)
    else:
        count = int(.05 * len(targets))

    targets = random.sample(targets, count)

    tester = Tester()
    for target in targets:
        tester.run_test(target)

    results = tester.results
    total = len(results)
    ok = len([ x for x in results.values() if x ])

    if args.output == 'verbose':
        print('{ok} / {total} OK'.format(ok=ok, total=total))
    elif args.output == 'percent':
        percent = 100.0 * ok / total
        print('{percent:.2f}'.format(percent=percent))
    elif args.output == 'count':
        print('{ok}'.format(ok=ok))
    elif args.output == 'count_total':
        print('{ok} {total}'.format(ok=ok, total=total))

    if args.fail_threshold is not None:
        threshold = args.fail_threshold
        if isinstance(threshold, float):
            threshold = int(threshold * total)
        if ok < threshold:
            sys.exit(1)

if __name__ == '__main__':
    main()
