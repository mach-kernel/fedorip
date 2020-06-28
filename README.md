# fedorip

Use src.fedoraproject.org API to attempt to automate clone + build of packages, for inventory in SGUG RSE.

## Getting Started

Export stuff (try to use absolute paths):

```py
FR_RSE_REPO_PATH = os.environ.get('FR_RSE_REPO_PATH')
FR_RPMHOME_PATH = os.environ.get('FR_RPMHOME_PATH')
FR_OUTRPM_PATH = os.environ.get('FR_OUTRPM_PATH')
```

Send it:

```bash
# TODO hammy spec
python -m pip install --user -r requirements.txt
python rippums.py --fetch-pattern 'perl-*'
```