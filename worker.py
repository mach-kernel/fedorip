#!/usr/bin/env python

# fedorip.py (now with 150% more abuses)
# github.com/mach-kernel

import os
import re
import subprocess
import glob
import shutil
from distutils import dir_util
from distutils import file_util
import sys
import logging
import json

from handlers.spec_success import handle_get_outrpms
from handlers.spec_failed import handle_perl_missing_dep

from fedorip_env import *
from vcs import rip_from_fedora_vcs

EMPTY_STATE = {
  'rpms_out': [],
  'srpms_out': []
}

class Worker:
  state = EMPTY_STATE.copy()
  log = logging.getLogger('fedorip')

  spec_fixes = [
    "s/perl(:MODULE_COMPAT.*$/perl(:MODULE_COMPAT_%(perl -V:version | sed 's,[^0-9^\.]*,,g'))/"
  ]

  def __init__(self):
    self.log.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    self.log.addHandler(sh)

  def clean_rpmhome(self):
    dirs = list(map(lambda d: '%s/%s' % (FR_RPMHOME_PATH, d)), [
      'SOURCES',
      'SPRMS',
      'RPMS',
      'BUILD',
      'BUILDROOT',
    ])

    for dir in dirs:
      dir_util.remove_tree(dir)    

  def handle_build(self, pkg_name):
    try_build = rip_from_fedora_vcs(pkg_name)

    if not try_build:
      return EMPTY_STATE

    spec_paths = glob.glob(
      '%s/packages/%s/SPECS/*.spec' % (FR_RSE_REPO_PATH, pkg_name)
    )

    dir_util.copy_tree(
      '%s/packages/%s/SOURCES' % (FR_RSE_REPO_PATH, pkg_name),
      '%s/SOURCES/' % FR_RPMHOME_PATH,
      update=True
    )

    if not len(spec_paths):
      raise FileNotFoundError(('Cannot find spec in %s', spec_paths))

    for sed_expr in self.spec_fixes:
      sed_cmd = '/usr/sgug/bin/sed -ie "%s" %s' % (sed_expr, spec_paths[0])
      self.log.info(subprocess.getoutput(sed_cmd))

    rpmbuild_process = subprocess.Popen(
      [
        '/usr/sgug/bin/rpmbuild',
        '--undefine=_disable_source_fetch',
        '--nocheck',
        '-ba',
        spec_paths[0]
      ],
      env=os.environ.copy(),
      stderr=subprocess.PIPE,
      stdout=subprocess.PIPE
    )

    while rpmbuild_process.poll() is None:
      print(rpmbuild_process.stdout.readline().decode(), end='')
      print(rpmbuild_process.stderr.readline().decode(), end='')

    if (rpmbuild_process.returncode == 0):
      self.handle_get_outrpms(spec_paths[0], pkg_name)
    else:
      self.log.error('Build failed, skipping %s', pkg_name)
    
    return self.state

  def handle_get_outrpms(self, spec_path, pkg_name):
    outfiles = glob('%s/RPMS/**/*.rpm', recursive=True).extend(glob('%s/SRPMS/**/*.rpm', recursive=True))

    if not len(outfiles):
      return

    self.log.info('Found %d output RPMs' % len(outfiles))
    move_rpms(outfiles)
    for outrpm in outfiles:
      meta = {
        'name': pkg_name,
        'rpm': os.path.basename(outrpm),
        'spec': spec_path
      }

      if '.src.rpm' in outrpm:
        self.state['srpms_out'].append(meta)
      else:
        self.state['rpms_out'].append(meta)

  def move_rpms(self, paths):
    if not os.path.exists(FR_OUTRPM_PATH):
      os.mkdir(FR_OUTRPM_PATH)

    if not os.path.exists(FR_OUTSRPM_PATH):
      os.mkdir(FR_OUTSRPM_PATH)

    for rpm_path in paths:
      if '.src.rpm' in rpm_path:
        shutil.move(rpm_path, FR_OUTSRPM_PATH)
      else:
        shutil.move(rpm_path, FR_OUTRPM_PATH)