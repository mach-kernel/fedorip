import os
import re
import subprocess
from glob import glob
import shutil
from distutils import dir_util
from distutils import file_util
import sys
import logging
import json

from support.env import *
from support.vcs import vcs_clone_and_stage

log = logging.getLogger('fedorip/builder')
log.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
log.addHandler(sh)

class Builder:
  # TODO: How do we handle this, except not like this
  spec_fixes = [
    "s/perl(:MODULE_COMPAT.*$/perl(:MODULE_COMPAT_%(perl -V:version | sed 's,[^0-9^\.]*,,g'))/"
  ]

  def __init__(self):
    self.state = {
      'rpms_out': [],
      'srpms_out': []
    }

  # TODO: Should look into trying:
  # rpmbuild --define "_topdir rpmbuild_but_just_for_pkg_x"
  # Would be preferable since it would allow you to run multiple workers
  # (don't worry about trampling dirs)
  def clean_rpmhome(self):
    dirs = list(map(lambda d: '%s/%s' % (FR_RPMHOME_PATH, d), [
      'SOURCES',
      'SRPMS',
      'RPMS',
      'BUILD',
      'BUILDROOT'
    ]))

    for dir in dirs:
      log.info('Cleaning %s' % dir)
      dir_util.remove_tree(dir)
      os.mkdir(dir)

  def build(self, pkg_name):
    try_build = vcs_clone_and_stage(pkg_name)

    if not try_build:
      return self.state

    self.clean_rpmhome()

    spec_paths = glob(
      '%s/packages/%s/SPECS/*.spec' % (FR_RSE_REPO_PATH, pkg_name)
    )

    dir_util.copy_tree(
      '%s/packages/%s/SOURCES' % (FR_RSE_REPO_PATH, pkg_name),
      '%s/SOURCES/' % FR_RPMHOME_PATH,
      update=True
    )

    if not len(spec_paths):
      return self.state

    for sed_expr in self.spec_fixes:
      sed_cmd = '/usr/sgug/bin/sed -ie "%s" %s' % (sed_expr, spec_paths[0])
      log.info(subprocess.getoutput(sed_cmd))

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
      out, err = rpmbuild_process.communicate()
      print(out.decode(), end='')
      print(err.decode(), end='')

    if (rpmbuild_process.returncode == 0):
      self.handle_get_outrpms(spec_paths[0], pkg_name)
    else:
      log.error('Build failed, skipping %s', pkg_name)
    
    return self.state

  def handle_get_outrpms(self, spec_path, pkg_name):
    outfiles = glob('%s/RPMS/**/*.rpm' % FR_RPMHOME_PATH, recursive=True)
    outfiles.extend(glob('%s/SRPMS/**/*.rpm' % FR_RPMHOME_PATH, recursive=True))

    if not len(outfiles):
      return

    log.info('Found %d output RPMs' % len(outfiles))
    self.move_rpms(outfiles)
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

    for rpm_path in paths:
      shutil.move(rpm_path, FR_OUTRPM_PATH)