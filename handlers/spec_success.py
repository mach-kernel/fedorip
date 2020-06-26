import re
import logging

log = logging.getLogger('fedorip')
log.setLevel(logging.DEBUG)

def handle_get_outrpms(spec_path, pkg_name, rpm_output):
  outfiles = re.findall(r'(?<=Wrote: ).+\.rpm', rpm_output)
  if not len(outfiles):
    return

  log.info('Found %d output RPMs' % len(outfiles))
  for outrpm in outfiles:
    meta = {
      'name': pkg_name,
      'path': outrpm,
      'spec': spec_path
    }

    if '.src.rpm' in outrpm:
      srpms_out.append(meta)
    else:
      rpms_out.append(meta)
