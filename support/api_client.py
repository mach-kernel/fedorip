import json
import logging

from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError

FR_FEDORA_API_URL = 'https://src.fedoraproject.org/api/0'
FR_FEDORA_VCS_FILE_URL = 'https://src.fedoraproject.org/rpms/perl-HTTP-Date/raw/master/f/perl-HTTP-Date.spec'

log = logging.getLogger('fedorip/client')
log.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
log.addHandler(sh)

def fclient_search_pkgs(pattern, page=1, short=1):
  query = {
    'pattern': pattern,
    'short': short,
    'page': page,
  }
  url = '%s/projects?%s' % (FR_FEDORA_API_URL, urlencode(query))

  try:
    return json.loads(urlopen(url).read())
  except HTTPError as e:
    log.error('HTTP request to %s failed' % url)
    log.error(e.read())

def fclient_all_pkgs(pattern):
  response = fclient_search_pkgs(pattern)
  page = 1
  max_page = response['pagination']['pages']

  yield response

  while page < max_page:
    log.info('Fetching page %d of %d' % (page, max_page))
    response = fclient_search_pkgs('*perl-*', pattern)
    yield response
    page += 1

def fclient_raw_spec_for_pkg(pkgname):
  url = 'https://src.fedoraproject.org/rpms/%s/raw/master/f/%s.spec' % (
    pkgname,
    pkgname
  )
  try:
    return urlopen(url).read().decode()
  except HTTPError as e:
    log.error('HTTP request to %s failed' % url)
    log.error(e.read())
    return ''