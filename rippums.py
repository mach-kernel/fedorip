#!/usr/bin/env python

import argparse
import json
import logging
import random
import subprocess
import os
import functools
import signal
import json

from support.builder import Builder
from support.env import *
from support.api_client import fclient_all_pkgs
from support.vcs import vcs_commit_and_push
from support.rpm import rpm_install_rpms, rpm_can_build

class Rippums:
  log = logging.getLogger('fedorip')
  builder = Builder()
  skiplist = []

  def __init__(self):
    self.log.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    self.log.addHandler(sh)

    if os.path.exists('skiplist.json'):
      skl = open('skiplist.json', 'r')
      self.skiplist = json.loads(skl.read())
      skl.close()

    signal.signal(signal.SIGINT, self.handle_sigint)
    
  def handle_sigint(self):
    self.log.error('OK! Stopping + dumping skiplist')
    f = open('skiplist.json', 'w')
    f.write(json.dumps(self.skiplist))
    f.close()

  def start(self, pattern):
    for frame in fclient_all_pkgs(pattern):      
      self.log.info(
        'QUERY: %s, PAGE: %d/%d' % (
          pattern,
          frame['pagination']['page'],
          frame['pagination']['pages']
        )
      )

      for pkg in frame['projects']:
        self.log.info('Attempting %s' % pkg['name'])

        if pkg['name'] in self.skiplist:
          self.log.info('Package %s in skiplist', pkg['name'])
          continue

        can_build = rpm_can_build(pkg['name'])

        if not can_build:
          self.log.info('Skipping %s', pkg['name'])
          self.skiplist.append(pkg['name'])
          continue

        rip_results = self.builder.build(pkg['name'])
        rip_results['installed'] = rpm_install_rpms(rip_results['rpms_out'])
        if not len(rip_results['installed']):
          self.skiplist.append(pkg['name'])
          continue

        vcs_commit_and_push(rip_results)

def parse_args():
  parser = argparse.ArgumentParser(description='rippums!!!!')
  parser.add_argument(
    '--fetch-pattern',
    help='Get all packages matching pattern, save to rippums.json',
    default=False,
    type=str,
    required=True
  )

  return parser.parse_args()

if __name__ == '__main__':
  args = parse_args()
  Rippums().start(args.fetch_pattern)