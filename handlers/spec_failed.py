import re

def handle_perl_missing_dep(fedorip, pkg_name, rpm_output):
  missing_deps = re.findall(r'(?<=perl\()(\S+(?=\)))', rpm_output)
  if len(missing_deps):
    fedorip.log.info('Found %d missing dependencies: %s' % (len(missing_deps), str(missing_deps)))
    mapped_deps = map(lambda d: 'perl-' + d.replace('::', '-'), missing_deps)
    if pkg_name not in fedorip.state['pkg_fail']:
      fedorip.state['pkg_queue'].append(pkg_name)
    for extend_dep in mapped_deps:
      if extend_dep not in fedorip.state['pkg_fail']:
        fedorip.state['pkg_queue'].append(extend_dep)