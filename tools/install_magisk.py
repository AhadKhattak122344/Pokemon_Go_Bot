"""Apply the pinned upstream temporary Magisk AVD setup to a debug emulator."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / '.tools'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--serial', default='emulator-5554')
args = parser.parse_args()
adb = ASSETS / 'android-sdk/platform-tools/adb.exe'
os.environ['ANDROID_SERIAL'] = args.serial
os.environ['ANDROID_USER_HOME'] = str(ASSETS / 'android-user')
os.environ['PATH'] = str(adb.parent) + os.pathsep + os.environ['PATH']

def shell(*command):
    return subprocess.check_output(
        [str(adb), '-s', args.serial, 'shell', *command],
        text=True, encoding='utf-8', errors='replace', timeout=30,
    ).strip()

for name, expected in {
    'Magisk-v30.7.apk': 'e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5',
    'magisk-source/build.py': 'd509cb1a11e64b7e3e2d01230051bc434cfb1c5d9875a57974233c4853face6e',
    'magisk-source/scripts/live_setup.sh': 'b3dc430c96718cd4a08e30282c6c57f3da026bc4e75de09e0a426eaed64a1e49',
}.items():
    if hashlib.sha256((ASSETS / name).read_bytes()).hexdigest() != expected:
        raise SystemExit(f'Checksum mismatch: {name}')

if shell('getprop', 'ro.kernel.qemu') != '1' or shell('getprop', 'ro.debuggable') != '1':
    raise SystemExit('Only a debuggable Android emulator is supported.')
if shell('getprop', 'ro.build.version.sdk') != '34' or shell('getprop', 'ro.product.cpu.abi') != 'x86_64':
    raise SystemExit('This wrapper is verified only for the project API 34 x86_64 Google APIs emulator.')
if shell('getenforce') == 'Disabled':
    raise SystemExit('The official setup requires SELinux enabled.')
if shell('id', '-u') != '0':
    subprocess.run([str(adb), '-s', args.serial, 'root'], check=True, timeout=30)
    subprocess.run([str(adb), '-s', args.serial, 'wait-for-device'], check=True, timeout=60)
    if shell('id', '-u') != '0':
        raise SystemExit('ADB root could not be enabled.')

# Invoke the upstream emulator operation directly, avoiding its unrelated Git/build setup.
source = ASSETS / 'magisk-source'
spec = importlib.util.spec_from_file_location('magisk_upstream', source / 'build.py')
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)
upstream.args = argparse.Namespace(build=False, apk=str(ASSETS / 'Magisk-v30.7.apk'),
                                   release=True, verbose=1)
upstream.force_out = True
upstream.no_color = True
out = source / 'out'
out.mkdir(exist_ok=True)
upstream.config['outdir'] = str(out)
os.chdir(source)
upstream.setup_avd()

deadline = time.monotonic() + 180
while shell('getprop', 'sys.boot_completed') != '1':
    if time.monotonic() >= deadline:
        raise SystemExit('Android did not finish restarting within 180 seconds.')
    time.sleep(3)
print('Magisk daemon:', shell('/debug_ramdisk/magisk', '-v'))
print('Magisk path:', shell('/debug_ramdisk/magisk', '--path'))
print('SELinux:', shell('getenforce'))
print('Temporary installation complete. Re-run this script after an emulator reboot.')
