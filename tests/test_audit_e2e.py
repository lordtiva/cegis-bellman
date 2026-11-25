"""End-to-end test running standalone auditor on exported certificate archive."""

import os
import subprocess
import sys


def test_standalone_auditor_if_archive_exists():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    archive = os.path.join(root, "certificates", "cegis_certificates.json.xz")
    auditor = os.path.join(root, "core", "audit_standalone.py")
    if not os.path.exists(archive):
        return
    r1 = subprocess.run([sys.executable, "-u", auditor, archive], check=False)
    assert r1.returncode == 0
    r2 = subprocess.run(
        [sys.executable, "-u", auditor, archive, "--pure-python", "--model", "mvs_canonical"],
        check=False,
    )
    assert r2.returncode == 0
