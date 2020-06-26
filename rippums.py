#!/usr/bin/env python

# rippums.py (where delusions become reality)

# uses src.fedoraproject.org api to grab packages matching a pattern
# uses fedorip to spawn jobs to walk a chain of packages
# installs then commits successfully built pkgs

import argparse
import json
import logging
import random
import subprocess
import os

from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError

log = logging.getLogger('rippums')
log.setLevel(logging.DEBUG)

sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

log.addHandler(sh)

FR_FEDORA_API_URL = 'https://src.fedoraproject.org/api/0'
pkg_queue = []

###############################################################################
# fedora API REST bindings

def fedora_search_pkgs(pattern, page=1, short=1):
  query = {
    'pattern': pattern,
    'short': short,
    'page': page,
  }
  url = '%s/projects?%s' % (FR_FEDORA_API_URL, urlencode(query))

  try:
    return json.loads(urlopen(url).read())
  except HTTPError as e:
    log.error('HTTP request to %s failed' % url)

def all_fedora_pkgs(pattern):
  response = fedora_search_pkgs(pattern)
  page = 1
  max_page = response['pagination']['pages']

  yield response

  while page < max_page:
    log.info('Fetching page %d of %d' % (page, max_page))
    response = fedora_search_pkgs('*perl-*', page)
    yield response
    page += 1

def dump_pkg_list(pattern):
  packages = []
  for frame in all_fedora_pkgs(pattern):
    packages.extend(frame['projects'])
  
  log.info('Got %d packages' % len(packages))
  f = open('rippums.json', 'w')
  f.write(json.dumps(packages))
  exit(0)

###############################################################################
# RPMs

def run_fedorip(package):
  process = subprocess.Popen(
    ['python', './fedorip.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=os.environ.copy()
  )
  while not process.poll():
    print(process.stderr.readline())
  return json.loads(process.stdout.readlines())

def install_rpms(fedorip_out):
  success_rpms = []

  for rpm in fedorip_out['rpms']:
    status, output = subprocess.run([
      '/usr/sgug/bin/sudo',
      '/usr/sgug/bin/rpm',
      '-ivh',
      '--nodeps',
      rpm['path']
    ]);

    if status == 0:
      success_rpms.append(rpm)

  log.info('Successfully installed %d' % len(success_rpms))
  pkg_queue = filter(lambda p: p['name'] not in success_rpms, pkg_queue)
  success_rpms

def rip_event_loop():
  while len(pkg_queue):
    select = random.randrange(0, len(pkg_queue))
    package = pkg_queue[select]
    rip_results = run_fedorip(package)
    rip_results['installed'] = install_rpms(rip_results)
  
def start(path):
   f = open(path, 'r')
   pkg_queue.extend(f.read())

def parse_args():
  parser = argparse.ArgumentParser(description='rippums!!!!')

  group = parser.add_mutually_exclusive_group()
  group.add_argument(
    '--fetch-pattern',
    help='Get all packages matching pattern, save to rippums.json',
    default=False,
    type=str,
  )
  group.add_argument(
    '--pkg-list-path',
    help='Path to list of packages to target',
    default='rippums.json'
  )

  return parser.parse_args()

if __name__ == '__main__':
  args = parse_args()
  if args.fetch_pattern:
    dump_pkg_list(args.fetch_pattern)
  elif args.pkg_list_path:
    start(args.pkg_list_path)
