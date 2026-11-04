"""Run a localhost-only macOS preview for the current login session.

Stages public site assets outside Documents so launchd does not need additional
macOS privacy permissions. It installs no login item and changes no network policy.
"""
import argparse
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'com.terreaux.chemical-waves.local'
SITE = Path('/tmp/terreaux-chemical-waves-site')
PLIST = Path('/tmp/com.terreaux.chemical-waves.local.plist')
URL = 'http://127.0.0.1:8766/'


def main(action):
    if sys.platform != 'darwin':
        raise SystemExit('This helper uses macOS launchd. Elsewhere use python3 -m http.server --bind 127.0.0.1.')
    domain = f'gui/{os.getuid()}'
    target = f'{domain}/{LABEL}'
    status = subprocess.run(['launchctl', 'print', target], capture_output=True)
    if action == 'status':
        print(f'{URL} — session service '+('loaded' if status.returncode == 0 else 'stopped'))
        return
    if action == 'stop':
        if status.returncode == 0:
            subprocess.run(['launchctl', 'bootout', target], check=True)
        print('Local showcase service stopped.')
        return
    SITE.mkdir(exist_ok=True)
    for name in ['index.html', 'app.js', 'style.css', 'LICENSE', 'README.md', 'data', 'volume', 'engine', 'docs']:
        source = ROOT/name
        if source.is_dir():
            shutil.copytree(source, SITE/name, dirs_exist_ok=True)
        elif source.is_file():
            shutil.copy2(source, SITE/name)
    config = {'Label': LABEL,
              'ProgramArguments': ['/usr/bin/python3', '-m', 'http.server', '8766', '--bind', '127.0.0.1', '--directory', str(SITE)],
              'RunAtLoad': True, 'KeepAlive': True,
              'StandardOutPath': '/tmp/terreaux-chemical-waves-http.log',
              'StandardErrorPath': '/tmp/terreaux-chemical-waves-http.log'}
    PLIST.write_bytes(plistlib.dumps(config))
    if status.returncode == 0:
        subprocess.run(['launchctl', 'bootout', target], check=True)
    subprocess.run(['launchctl', 'bootstrap', domain, str(PLIST)], check=True)
    for _ in range(30):
        try:
            with urllib.request.urlopen(URL, timeout=1) as response:
                if response.status == 200:
                    print(f'{URL} — running until logout, restart, or explicit stop.')
                    print(f'Public site assets staged in {SITE}. Run start again to refresh from the repository.')
                    return
        except OSError:
            time.sleep(.1)
    raise SystemExit('Service started but HTTP verification failed; inspect /tmp/terreaux-chemical-waves-http.log.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop', 'status'])
    main(parser.parse_args().action)
