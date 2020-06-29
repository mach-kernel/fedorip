import subprocess
import logging
import functools

from support.api_client import fclient_raw_spec_for_pkg
from support.env import *
from pyrpm.spec import Spec, replace_macros

log = logging.getLogger('fedorip/rpm')
log.setLevel(logging.DEBUG)

sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

log.addHandler(sh)

def rpm_can_satisfy(dep):
  status, _out = subprocess.getstatusoutput(' '.join([
    '/usr/sgug/bin/rpm',
    '-qi',
    '--whatprovides',
    dep
  ]))

  return status == 0

def rpm_can_build(pkgname):
  spec_str = fclient_raw_spec_for_pkg(pkgname)
  if not len(spec_str):
    return False
  
  spec = Spec.from_string(spec_str)
  exclude = spec.packages_dict.keys()

  dep_lists = list(map(lambda pkg: pkg.requires, spec.packages_dict.values()))
  deps = functools.reduce(lambda a,b: a+b, dep_lists)

  for dep in deps:
    dep_name = str(dep).split(' ')[0]
    if dep_name in exclude:
      continue
    if not rpm_can_satisfy(dep_name):
      return False
  
  return True

def rpm_install_rpms(rpms):
  success_rpms = []

  for rpm in rpms:
    status, output = subprocess.getstatusoutput(' '.join([
      '/usr/sgug/bin/sudo',
      '/usr/sgug/bin/rpm',
      '-ivh',
      '--nodeps',
      '%s/%s' % (FR_OUTRPM_PATH, rpm['rpm'])
    ]))

    log.info(output)

    if status == 0 or 'is already installed' in output:
      success_rpms.append(rpm)

  log.info('Installed %d' % len(success_rpms))
  return success_rpms