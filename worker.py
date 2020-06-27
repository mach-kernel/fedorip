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

class Fedorip:
  state = {}
  log = logging.getLogger('fedorip')
  FR_RSE_REPO_PATH = os.environ.get('FR_RSE_REPO_PATH')
  FR_RPMHOME_PATH = os.environ.get('FR_RPMHOME_PATH')
  FR_FEDORA_CLONE_URI = 'https://src.fedoraproject.org/rpms'
  FR_TMP_PATH = '/var/tmp/fedorip'

  spec_fail_handlers = [
    handle_perl_missing_dep,
  ]

  spec_success_handlers = [
    handle_get_outrpms
  ]

  spec_fixes = [
    "s/perl(:MODULE_COMPAT.*$/perl(:MODULE_COMPAT_%(perl -V:version | sed 's,[^0-9^\.]*,,g'))/"
  ]

  def __init__(self):
    self.state = {
      'pkg_queue': [],
      'pkg_success': [],
      'pkg_fail': [],
      'rpms_out': [],
      'srpms_out': []
    }

    self.log.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    self.log.addHandler(sh)

  def from_args(self):
    shutil.rmtree(self.FR_TMP_PATH)
    os.mkdir(self.FR_TMP_PATH)

    self.state['pkg_queue'].append(sys.argv[1])
    self.rip_event_loop()

    print(json.dumps(self.state))
    exit(0)

  def rip_from_fedora_vcs(self, pkg_name):
    url = '%s/%s.git' % (self.FR_FEDORA_CLONE_URI, pkg_name)
    target_path = '%s/%s' % (self.FR_TMP_PATH, pkg_name)
    spec_path = '%s/packages/%s/SPECS/' % (self.FR_RSE_REPO_PATH, pkg_name)
    source_path = '%s/packages/%s/SOURCES/' % (self.FR_RSE_REPO_PATH, pkg_name)

    if not (os.path.exists(target_path)):
      clcmd = '/usr/sgug/bin/git clone %s %s' % (url, target_path)
      clstatus, clout = subprocess.getstatusoutput(clcmd)

      if clstatus:
        return False

    if not (os.path.exists(spec_path)):
      os.makedirs(spec_path)
    
    if not (os.path.exists(source_path)):
      os.makedirs(source_path)

    for spec_file in glob.glob('%s/%s/**/*.spec' % (self.FR_TMP_PATH, pkg_name), recursive=True):
      file_util.copy_file(
        spec_file,
        spec_path,
        update=True
      )

    for source_file in glob.glob('%s/%s/**/*' % (self.FR_TMP_PATH, pkg_name), recursive=True):
      if '.spec' in source_file:
        continue
      file_util.copy_file(
        source_file,
        source_path,
        update=True
      )

    return True

  def handle_build(self, pkg_name):
    spec_paths = glob.glob(
      '%s/packages/%s/SPECS/*.spec' % (self.FR_RSE_REPO_PATH, pkg_name)
    )

    dir_util.copy_tree(
      '%s/packages/%s/SOURCES' % (self.FR_RSE_REPO_PATH, pkg_name),
      '%s/SOURCES/' % self.FR_RPMHOME_PATH,
      update=True
    )

    if not len(spec_paths):
      raise FileNotFoundError(('Cannot find spec in %s', spec_paths))

    for sed_expr in self.spec_fixes:
      sed_cmd = '/usr/sgug/bin/sed -ie "%s" %s' % (sed_expr, spec_paths[0])
      self.log.info(subprocess.getoutput(sed_cmd))

    build_command = '/usr/sgug/bin/rpmbuild --undefine=_disable_source_fetch --nocheck -ba %s' % spec_paths[0]
    rpmstatus, rpmoutput = subprocess.getstatusoutput(build_command)
    self.log.info(rpmoutput)

    if (rpmstatus == 0):
      self.state['pkg_success'].append(pkg_name)
      for handler in self.spec_success_handlers:
        handler(fedorip, spec_paths[0], pkg_name, rpmoutput)
    else:
      self.state['pkg_fail'].append(pkg_name)
      self.log.warning('%s build failed -- missing dependencies?' % pkg_name)
      for handler in self.spec_fail_handlers:
        handler(self, pkg_name, rpmoutput)

  def rip_event_loop(self):
    while len(self.state['pkg_queue']) > 0:
      remain = len(self.state['pkg_queue'])
      current_pkg = self.state['pkg_queue'].pop()
      self.log.info('Working on %s, %d left' % (current_pkg, remain))
      try_build = self.rip_from_fedora_vcs(current_pkg)
      if try_build:
        self.handle_build(current_pkg)


if __name__ == '__main__':
  if len(sys.argv) <= 1:
    print('ERROR: Provide src.fedoraproject.org repo pkg-name')
    exit(1)
  Fedorip().from_args()