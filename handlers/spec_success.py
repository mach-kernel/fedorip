import re
import logging

def handle_get_outrpms(fedorip, spec_path, pkg_name, rpm_output):
  outfiles = re.findall(r'(?<=Wrote: ).+\.rpm', rpm_output)
  if not len(outfiles):
    return

  fedorip.log.info('Found %d output RPMs' % len(outfiles))
  for outrpm in outfiles:
    meta = {
      'name': pkg_name,
      'path': outrpm,
      'spec': spec_path
    }

    if '.src.rpm' in outrpm:
      fedorip.state['srpms_out'].append(meta)
    else:
      fedorip.state['rpms_out'].append(meta)
