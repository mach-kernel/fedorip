#!/usr/bin/env python

import argparse
import json
import logging
import random
import subprocess
import os
import functools

from support.builder import Builder
from support.env import *
from support.api_client import fclient_all_pkgs
from support.vcs import vcs_commit_and_push
from support.rpm import rpm_install_rpms, rpm_can_build

class Rippums:
  log = logging.getLogger('rippums')
  builder = Builder()

  def __init__(self):
    self.log.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    self.log.addHandler(sh)

  def start(self, pattern):
    for frame in fclient_all_pkgs(pattern):      
      self.log.info(
        'QUERY: %s, PAGE: %d/%d' % (
          pattern,
          frame['pagination']['page'],
          frame['pagination']['pages']
        )
      )

      for pkg in frame['packages']:
        self.log.info('Attempting %s' % pkg['name'])
        can_build = rpm_can_build(pkg['name'])

        if not can_build:
          self.log.info('Skipping %s', pkg['name'])
          continue

        rip_results = self.builder.build(pkg['name'])
        rip_results['installed'] = rpm_install_rpms(rip_results['rpms_out'])
        vcs_commit_and_push(rip_results['installed'])

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