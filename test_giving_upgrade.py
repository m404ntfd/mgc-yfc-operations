"""Exercise the real updater in an isolated preview build; never change release versions."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='giving-upgrade-build-') as tmp:
    target=Path(tmp)
    files=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
    for name in filter(None,files):
        source=root/name
        if not source.is_file():continue
        destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(source.read_bytes())
    # A test-only higher version is needed because the updater correctly rejects
    # installing an identical version. No production VERSION is changed.
    (target/'VERSION').write_text('99.0.0\n')
    subprocess.run([sys.executable,'build_release.py'],cwd=target,check=True)
    subprocess.run([sys.executable,'test_retail_release_upgrade.py'],cwd=target,check=True)
