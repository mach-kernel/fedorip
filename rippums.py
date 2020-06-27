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

from worker import Worker
from fedorip_env import *
from fedora_api_client import all_fedora_pkgs, get_raw_spec_for_pkg
from vcs import commit_and_push
from pyrpm.spec import Spec, replace_macros

class Rippums:
  log = logging.getLogger('rippums')

  def __init__(self):
    self.log.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    self.log.addHandler(sh)

  def run_fedorip(self, package):
    worker = Worker()
    worker.state['pkg_queue'].append(package)
    return worker.rip_event_loop()

  def install_rpms(self, fedorip_out):
    success_rpms = []

    for rpm in fedorip_out['rpms_out']:
      status, output = subprocess.getstatusoutput(' '.join([
        '/usr/sgug/bin/sudo',
        '/usr/sgug/bin/rpm',
        '-ivh',
        '--nodeps',
        rpm['path']
      ]));

      log.info(output)

      if status == 0:
        success_rpms.append(rpm)

    log.info('Installed %d' % len(success_rpms))
    return success_rpms

  def can_build(self, pkgname):
    spec_str = get_raw_spec_for_pkg(pkgname)
    if not len(spec_str):
      return False
    
    spec = Spec.from_string(spec_str)

  def rip_event_loop(self, pattern):
    for frame in all_fedora_pkgs(pattern):      
      log.info(
        'QUERY: %s, PAGE: %d/%d' % (
          pattern,
          frame['pagination']['page'],
          frame['pagination']['pages']
        )
      )

      for pkg in frame['packages']:
        log.info('Attempting %s' % pkg['name'])
        can_build = self.can_build(pkg['name'])

        if not can_build:
          log.info('Skipping %s', pkg['name'])
          continue

        rip_results = self.run_fedorip(pkg['name'])
        rip_results['installed'] = install_rpms(rip_results)
        commit_and_push(rip_results['installed'])
    
  def start(self, path):
    rip_event_loop(path)


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
  Rippums().rip_event_loop(args.fetch_pattern)