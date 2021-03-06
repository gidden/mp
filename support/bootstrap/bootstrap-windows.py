# Set up build environment on 64-bit Windows.

from __future__ import print_function
import os, shutil, tempfile
from bootstrap import *
from glob import glob
from subprocess import check_call, check_output

# The timer module should be imported after bootstrap which sets up sys.path.
import ctxtimer

# Add Python to PATH.
python_dir = r'C:\Python27'
if os.path.exists(python_dir) and not installed('python'):
  add_to_path(python_dir + r'\python')
  add_to_path(python_dir + r'\Scripts', None, True)

install_cmake('cmake-3.1.0-win32-x86.zip')
install_maven()

# Install .NET Framework 4 for msbuild.
if not os.path.exists(r'\Windows\Microsoft.NET\Framework64\v4.0.30319'):
  with download(
      'http://download.microsoft.com/download/9/5/A/' +
      '95A9616B-7A37-4AF6-BC36-D6EA96C8DAAE/dotNetFx40_Full_x86_x64.exe') as f:
    check_call([f, '/q', '/norestart'])

# Install 7zip.
sevenzip = r'C:\Program Files (x86)\7-Zip\7z.exe'
if not os.path.exists(sevenzip):
  with download('http://downloads.sourceforge.net/sevenzip/7z920.exe') as f:
    check_call([f, '/S'])

# Install Windows SDK.
if not os.path.exists(r'\Program Files\Microsoft SDKs\Windows\v7.1'):
  # Extract ISO.
  with download(
       'http://download.microsoft.com/download/F/1/0/'
       'F10113F5-B750-4969-A255-274341AC6BCE/GRMSDKX_EN_DVD.iso') as f:
    check_call([sevenzip, 'x', '-tudf', '-owinsdk', f])
  # Install SDK.
  check_call([r'winsdk\setup.exe', '-q'])
  shutil.rmtree('winsdk')

# Install MinGW.
def install_mingw(arch):
  bits = '64' if arch.endswith('64') else '32'
  if os.path.exists(r'\mingw' + bits):
    return
  with download(
      'http://sourceforge.net/projects/mingw-w64/files/' +
      'Toolchains%20targetting%20Win' + bits + '/Personal%20Builds/' +
      'mingw-builds/4.8.2/threads-win32/sjlj/' + arch +
      '-4.8.2-release-win32-sjlj-rt_v3-rev4.7z/download') as f:
    with ctxtimer.print_time("Installing MinGW" + bits):
      output = check_output([sevenzip, 'x', '-oC:\\', f])
      for line in output.split('\n'):
        if not line.startswith('Extracting '):
          print(line)

install_mingw('i686')
install_mingw('x86_64')

# Install 32-bit JDK.
if not os.path.exists(r'\Program Files (x86)\Java\jdk1.7.0_' + str(jdk_update)):
  url = '{}jdk-7u{}-windows-i586.exe'.format(jdk_download_url, jdk_update)
  with download(url, jdk_cookie) as f:
    check_call([f, '/s'])

# Install 64-bit JDK.
if not os.path.exists(r'\Program Files\Java\jdk1.7.0_' + str(jdk_update)):
  url = '{}jdk-7u{}-windows-x64.exe'.format(jdk_download_url, jdk_update)
  with download(url, jdk_cookie) as f:
    check_call([f, '/s'])

# Install LocalSolver.
for bits in [32, 64]:
  suffix = ' (x86)' if bits == 32 else ''
  dirname = 'localsolver_' + re.match('(.*)_.*', LOCALSOLVER_VERSION).group(1)
  install_dir = r'C:\Program Files{}\{}'.format(suffix, dirname)
  if os.path.exists(install_dir):
    continue
  try:
    tempdir = tempfile.mkdtemp()
    with download(
        'http://www.localsolver.com/downloads/' +
        'LocalSolver_{}_Win{}.exe'.format(LOCALSOLVER_VERSION, bits)) as f:
      check_call([sevenzip, 'x', '-o' + tempdir, f])
    shutil.move(os.path.join(tempdir, '$_OUTDIR'), install_dir)
  finally:
    shutil.rmtree(tempdir)
localsolver_license_dir = 'C:\\' + dirname
if not os.path.exists(localsolver_license_dir):
  os.mkdir(localsolver_license_dir)
with open(os.path.join(localsolver_license_dir, 'license.dat'), 'w') as f:
  f.write("FREE_TRIAL = 1\n")

# Copy optional dependencies.
opt_dir = r'\opt\win64'
if os.path.exists(opt_dir):
  for entry in os.listdir(opt_dir):
    subdir = os.path.join(opt_dir, entry)
    for subentry in os.listdir(subdir):
      dest = os.path.join('C:\\', entry, subentry)
      if not os.path.exists(dest):
        source = os.path.join(subdir, subentry)
        print('Copying {} to {}'.format(source, dest))
        shutil.copytree(source, dest)

# Install pywin32 - buildbot dependency.
if not module_exists('win32api'):
  shutil.rmtree('pywin32', True)
  with download(
      'http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/' +
      'pywin32-219.win-amd64-py2.7.exe/download') as f:
    check_call([sevenzip, 'x', '-opywin32', f])
  site_packages_dir = os.path.join(python_dir, r'lib\site-packages')
  for path in glob('pywin32/PLATLIB/*') + glob('pywin32/SCRIPTS/*'):
    shutil.move(path, site_packages_dir)
  shutil.rmtree('pywin32')
  import pywin32_postinstall
  pywin32_postinstall.install()
  os.remove(site_packages_dir + r'\pywin32_postinstall.py')

# Specifies whether to restart BuildBot service.
restart = False

import win32serviceutil
import _winreg as reg

buildslave_dir = r'\buildslave'
if not os.path.exists(buildslave_dir):
  install_buildbot_slave('win2008', buildslave_dir, python_dir + r'\Scripts', True)

  # Set buildslave parameters.
  with reg.CreateKey(reg.HKEY_LOCAL_MACHINE,
      r'System\CurrentControlSet\services\BuildBot\Parameters') as key:
    reg.SetValueEx(key, 'directories', 0, reg.REG_SZ, buildslave_dir)

  # Install buildbot service.
  # The service is run under Local System account to allow it interact with
  # the desktop (--interactive) which is required for GUI tests.
  check_call([
    os.path.join(python_dir, 'python'),
    os.path.join(python_dir, r'Scripts\buildbot_service.py'),
    '--startup', 'auto', '--interactive', 'install'])
  win32serviceutil.StartService('BuildBot')
elif restart:
  print('Restarting BuildBot')
  win32serviceutil.RestartService('BuildBot')
