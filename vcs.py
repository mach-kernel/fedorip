import os
import subprocess
from distutils import file_util
from glob import glob
import logging
import json
from fedorip_env import *

log = logging.getLogger('fedorip/vcs')
log.setLevel(logging.DEBUG)

sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

log.addHandler(sh)

def rip_from_fedora_vcs(pkg_name):
  url = '%s/%s.git' % (FR_FEDORA_CLONE_URI, pkg_name)
  target_path = '%s/%s' % (FR_TMP_PATH, pkg_name)
  spec_path = '%s/packages/%s/SPECS/' % (FR_RSE_REPO_PATH, pkg_name)
  source_path = '%s/packages/%s/SOURCES/' % (FR_RSE_REPO_PATH, pkg_name)

  if not (os.path.exists(target_path)):
    clcmd = '/usr/sgug/bin/git clone %s %s' % (url, target_path)
    clstatus, clout = subprocess.getstatusoutput(clcmd)

    if clstatus:
      return False

  if not (os.path.exists(spec_path)):
    os.makedirs(spec_path)
  
  if not (os.path.exists(source_path)):
    os.makedirs(source_path)

  for spec_file in glob('%s/%s/**/*.spec' % (FR_TMP_PATH, pkg_name), recursive=True):
    file_util.copy_file(
      spec_file,
      spec_path,
      update=True
    )

  for source_file in glob('%s/%s/**/*' % (FR_TMP_PATH, pkg_name), recursive=True):
    if '.spec' in source_file:
      continue
    file_util.copy_file(
      source_file,
      source_path,
      update=True
    )

  return True

def commit_and_push(rip_results):
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