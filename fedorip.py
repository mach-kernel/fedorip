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

log = logging.getLogger('fedorip')
log.setLevel(logging.DEBUG)

sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

log.addHandler(sh)

# Configuration
FR_RSE_REPO_PATH = os.environ.get('FR_RSE_REPO_PATH')
FR_RPMHOME_PATH = os.environ.get('FR_RPMHOME_PATH')
FR_FEDORA_CLONE_URI = 'https://src.fedoraproject.org/rpms'
FR_TMP_PATH = '/var/tmp/fedorip'

pkg_stack = []
pkg_success = []
pkg_fail = []

rpms_out = []
srpms_out = []

###############################################################################
# Handle failed builds

def handle_perl_missing_dep(pkg_name, rpm_output):
  missing_deps = re.findall(r'(?<=perl\()\w+::?\w+(?=\))', rpm_output)
  if len(missing_deps):
    log.info('Found %d missing dependencies: %s' % (len(missing_deps), str(missing_deps)))
    mapped_deps = map(lambda d: 'perl-' + d.replace('::', '-'), missing_deps)
    if pkg_name not in pkg_fail:
      pkg_stack.append(pkg_name)
    pkg_stack.extend(mapped_deps)

spec_fail_handlers = [
  handle_perl_missing_dep,
]

###############################################################################
# Handle successful builds

def handle_get_outrpms(pkg_name, rpm_output):
  outfiles = re.findall(r'(?<=Wrote: ).+\.rpm$', rpm_output)
  if not len(outfiles):
    return

  log.info('Found %d output RPMs' % len(outfiles))
  for outrpm in outfiles:
    if '.src.rpm' in outrpm:
      srpms_out.append(outrpm)
    else:
      rpms_out.append(outrpm)

spec_success_handlers = [
  handle_get_outrpms
]

###############################################################################
# Apply sed rules to specs before running rpmbuild

spec_fixes = [
  "s/perl(:MODULE_COMPAT.*$/perl(:MODULE_COMPAT_%(perl -V:version | sed 's,[^0-9^\.]*,,g'))/"
]

###############################################################################

def rip_from_fedora_vcs(pkg_name):
  url = '%s/%s.git' % (FR_FEDORA_CLONE_URI, pkg_name)
  target_path = '%s/%s' % (FR_TMP_PATH, pkg_name)
  spec_path = '%s/packages/%s/SPECS/' % (FR_RSE_REPO_PATH, pkg_name)
  source_path = '%s/packages/%s/SOURCES/' % (FR_RSE_REPO_PATH, pkg_name)

  if not (os.path.exists(target_path)):
    subprocess.check_call(['/usr/sgug/bin/git', 'clone', url, target_path])

  if not (os.path.exists(spec_path)):
    os.makedirs(spec_path)
  
  if not (os.path.exists(source_path)):
    os.makedirs(source_path)

  for spec_file in glob.glob('%s/%s/**/*.spec' % (FR_TMP_PATH, pkg_name), recursive=True):
    file_util.copy_file(
      spec_file,
      spec_path,
      update=True
    )

  for source_file in glob.glob('%s/%s/**/*' % (FR_TMP_PATH, pkg_name), recursive=True):
    if '.spec' in source_file:
      continue
    file_util.copy_file(
      source_file,
      source_path,
      update=True
    )

def handle_build(pkg_name):
  spec_path = glob.glob(
    '%s/packages/%s/SPECS/*.spec' % (FR_RSE_REPO_PATH, pkg_name)
  )

  dir_util.copy_tree(
    '%s/packages/%s/SOURCES' % (FR_RSE_REPO_PATH, pkg_name),
    '%s/SOURCES/' % FR_RPMHOME_PATH,
    update=True
  )

  if not len(spec_path):
    raise FileNotFoundError(('Cannot find spec in %s', spec_path))

  for sed_expr in spec_fixes:
    sed_cmd = '/usr/sgug/bin/sed -ie "%s" %s' % (sed_expr, spec_path[0])
    log.info(subprocess.getoutput(sed_cmd))

  build_command = 'rpmbuild --undefine=_disable_source_fetch --nocheck -ba %s' % spec_path[0]
  rpmstatus, rpmoutput = subprocess.getstatusoutput(build_command)

  log.info(rpmoutput);
  
  if (rpmstatus == 0):
    pkg_success.append(pkg_name)
    for handler in spec_success_handlers:
      handler(pkg_name, rpmoutput)
  else:
    pkg_fail.append(pkg_name)
    log.warning('%s build failed -- missing dependencies?' % pkg_name)
    for handler in spec_fail_handlers:
      handler(pkg_name, rpmoutput)

def rip_event_loop():
  while len(pkg_stack) > 0:
    remain = len(pkg_stack)
    current_pkg = pkg_stack.pop()
    log.info('Working on %s, %d left' % (current_pkg, remain))
    rip_from_fedora_vcs(current_pkg)
    handle_build(current_pkg)

if __name__ == '__main__':
  if len(sys.argv) <= 1:
    print('ERROR: Provide src.fedoraproject.org repo pkg-name')
    exit(1)

  shutil.rmtree(FR_TMP_PATH)
  os.mkdir(FR_TMP_PATH)

  pkg_stack.append(sys.argv[1])
  rip_event_loop()

  result = {
    'success': pkg_success,
    'fail': pkg_fail,
    'rpms': rpms_out,
    'srpms': srpms_out
  }

  print(json.dumps(result))
  exit(0)