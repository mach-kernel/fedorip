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

from fedorip import Fedorip
from fedora_api_client import all_fedora_pkgs

class Rippums:
  FR_RSE_REPO_PATH = os.environ.get('FR_RSE_REPO_PATH')
  pkg_queue = []
  log = logging.getLogger('rippums')

  def __init__(self):
    self.log.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    self.log.addHandler(sh)

  def dump_pkg_list(self, pattern):
    packages = []
    for frame in all_fedora_pkgs(pattern):
      packages.extend(frame['projects'])
    
    log.info('Got %d packages' % len(packages))
    f = open('rippums.json', 'w')
    f.write(json.dumps(packages))
    exit(0)

  def run_fedorip(self, package):
    process = subprocess.Popen(
      ['/usr/sgug/bin/python', './fedorip.py', package['name']],
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      env=os.environ.copy(),
      cwd=os.getcwd()
    )
    worker = Fedorip()

    while process.poll() is None:
      print(process.stderr.readline().decode(), end='')
    return json.loads(process.stdout.read())

  def filter_and_save(self, success_rpms, pkg_list_path):
    success_names = map(lambda srpm: srpm['name'], success_rpms)
    newqueue = list(filter(lambda p: p['name'] not in success_names, pkg_queue))
    pkg_queue.clear()
    pkg_queue.extend(newqueue)
    f = open(pkg_list_path, 'w')
    f.write(json.dumps(pkg_queue))
    f.close()
    log.info('Saved queue progress, only %d left!' % len(pkg_queue))

  def install_rpms(self, fedorip_out):
    success_rpms = []

    for rpm in fedorip_out['rpms']:
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

  def commit_and_push(self, rip_results):
    for installed in rip_results['installed']:
      status, output = subprocess.getstatusoutput(' '.join([
        '/usr/sgug/bin/git',
        '--git-dir',
        '%s/.git' % (FR_RSE_REPO_PATH),
        '--work-tree',
        FR_RSE_REPO_PATH,
        'add',
        installed['spec']
      ]))

      log.info(output)
    
    status, output = subprocess.getstatusoutput(' '.join([
      '/usr/sgug/bin/git',
      '--git-dir',
      '%s/.git' % (FR_RSE_REPO_PATH),
      '--work-tree',
      FR_RSE_REPO_PATH,
      'commit',
      "-vm'%s'" % json.dumps(rip_results)
    ]))

    log.info(output)

    status, output = subprocess.getstatusoutput(' '.join([
      '/usr/sgug/bin/git',
      '--git-dir',
      '%s/.git' % (FR_RSE_REPO_PATH),
      '--work-tree',
      FR_RSE_REPO_PATH,
      'push',
      '-u',
      'origin',
      'HEAD'
    ]))

    log.info(output)

  def rip_event_loop(self, pkg_list_path):
    while len(pkg_queue):
      select = random.randrange(0, len(pkg_queue))
      package = pkg_queue[select]
      rip_results = run_fedorip(package)
      rip_results['installed'] = install_rpms(rip_results)
      filter_and_save(rip_results['installed'], pkg_list_path)
      commit_and_push(rip_results)
    
  def start(self, path):
    f = open(path, 'r')
    pkg_queue.extend(json.loads(f.read()))
    f.close()
    rip_event_loop(path)


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
    Rippums().dump_pkg_list(args.fetch_pattern)
  elif args.pkg_list_path:
    Rippums().start(args.pkg_list_path)
