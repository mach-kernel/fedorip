# fedorip
Abuse regexes to rip RPMs from src.fedoraproject.org. Split into a job that builds RPM specs and handles build failures, and another that orchestrates this into a workflow that ends up with commits on VCS.

## rippums (WIP)

- Grabs a list of all packages matching a pattern from Fedora API, saves to `rippums.json`
- Invoke `fedorip` and with successful packages
  - Install result binary RPM
  - Remove from JSON
- Commit to a Git branch staging the new changes (spec, srpm)

```
# Create a list to work off of
python3 rippums.py --fetch-pattern='*perl-*'
# Use it
python3 rippums.py --pkg-list-path=rippums.json
```

## fedorip

Clone + build RPM specs, try to recover from errors with scripted actions.

```
python fedorip.py perl-Module-Install
```

### Output

Look over `success` RPMs by hand before committing, check `rpmbuild/RPMS/mips` and `rpmbuild/RPMS/noarch` for your output RPMS.

```
{"success": ["perl-Canary-Stability", "perl-Test-Requires", "perl-Module-Runtime", "perl-App-FatPacker"], "fail": ["perl-Module-Install", "perl-YAML-Tiny", "perl-JSON-MaybeXS", "perl-JSON-XS", "perl-common-sense", "perl-Types-Serialiser", "perl-common-sense", "perl-Module-ScanDeps", "perl-Module-Pluggable"]}
```