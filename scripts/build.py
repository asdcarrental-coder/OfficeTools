"""Build with a controlled DLL search path, then test the actual executable."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
environment = os.environ.copy()
windows = Path(os.environ['SYSTEMROOT'])
# Do not collect same-named DLLs from unrelated apps on the developer's PATH.
environment['PATH'] = os.pathsep.join([str(Path(sys.executable).parent),
                                     str(windows / 'System32'), str(windows)])
for key in ('PYTHONPATH', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH'):
    environment.pop(key, None)
subprocess.run([sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm',
                '--windowed', '--onedir', '--noupx', '--name', 'OfficeTools',
                '--collect-all', 'pdf2docx', 'main.py'],
               cwd=root, env=environment, check=True)
report = root / 'build' / 'packaged-self-test.json'
report.unlink(missing_ok=True)
subprocess.run([str(root / 'dist/OfficeTools/OfficeTools.exe'), '--self-test', str(report)],
               cwd=root, env=environment, check=True, timeout=90)
import json
assert json.loads(report.read_text(encoding='utf-8'))['status'] == 'passed'
print('Build and packaged GUI/conversion tests passed.')
