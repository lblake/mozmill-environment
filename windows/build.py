#!/usr/bin/env python

import fileinput
import glob
import optparse
import os
import subprocess
import shutil
import sys
import urllib
import zipfile


URL_MSYS = "http://sourceforge.net/projects/mingw/files/MSYS/BaseSystem/msys-core/msys-1.0.11/MSYS-1.0.11.exe/download"
URL_MINTTY = "http://mintty.googlecode.com/files/mintty-1.0.1-msys.zip"
URL_VIRTUALENV = "https://bitbucket.org/ianb/virtualenv/raw/1.5.2/virtualenv.py"

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, "templates")
download_dir = os.path.join(base_dir, "downloads")

env_dir = os.path.join(base_dir, "mozmill-env")
msys_dir = os.path.join(env_dir, "msys")
python_dir = os.path.join(env_dir, "python")

def download(url, filename):
    '''Download a remote file from an URL to the specified local folder.'''

    try:
        urllib.urlretrieve(url, filename)
    except Exception, e:
        print "Failure downloading '%s': %s" % (url, str(e))
        raise


def make_relocatable(filepath):
    '''Remove python path from the Scripts'''

    files = glob.glob(filepath)

    for file in files:
        for line in fileinput.input(file, inplace=1):
            if fileinput.isfirstline() and line.startswith("#!"):
                # Only on Windows we have to set Python into unbuffered mode
                print "#!python -u"
            else:
                print line,

        fileinput.close()


parser = optparse.OptionParser()
(options, args) = parser.parse_args()

if not args:
    parser.error("Version of Mozmill to be installed is required as first parameter.")
mozmill_version = args[0]

print "Delete an already existent environment sub folder"
os.system("del /s /q %s" % (env_dir))

print "Download and install 'MSYS' in unattended mode. Answer questions with 'y' and 'n'."
# See: http://www.jrsoftware.org/ishelp/index.php?topic=setupcmdline
os.system("mkdir %s" % download_dir)
setup_msys = os.path.join(download_dir, "setup_msys.exe")
download(URL_MSYS, setup_msys)
subprocess.check_call([setup_msys, '/VERYSILENT', '/SP-', '/DIR=%s' % (msys_dir),
                       '/NOICONS' ])

print "Download and install 'mintty'"
mintty_path = os.path.join(download_dir, os.path.basename(URL_MINTTY))
download(URL_MINTTY, mintty_path)
zip = zipfile.ZipFile(mintty_path, "r")
zip.extract("mintty.exe", "%s\\bin" % (msys_dir))
zip.close()

print "Copy template files into environment"
os.system("xcopy /S /I /H %s %s" % (template_dir, env_dir))

print "Copy Python installation (including pythonXX.dll into environment"
os.system("xcopy /S /I /H %s %s\\python" % (sys.prefix, env_dir))
os.system("xcopy %s\\system32\\python*.dll %s" % (os.environ['WINDIR'], python_dir))

print "Download 'virtualenv' and create new virtual environment"
virtualenv_path = os.path.join(download_dir, os.path.basename(URL_VIRTUALENV))
filename = download(URL_VIRTUALENV, virtualenv_path)
subprocess.check_call(["python", filename, "--no-site-packages", "mozmill-env"])

print "Reorganizing folder structure"
os.system("move /y %s\\Scripts %s" % (env_dir, python_dir))
os.system("rd /s /q %s\\Lib\\site-packages" % (python_dir))
os.system("move /y %s\\Lib\\site-packages %s\\Lib" % (env_dir, python_dir))
os.system("rd /s /q %s\\Lib" % (env_dir))
make_relocatable("%s\\Scripts\\*.py" % (python_dir))

print "Installing required Python modules"
subprocess.check_call(["%s\\run.cmd" % env_dir, "pip", "install",
                       "--global-option='--pure'", "mercurial==1.9.3"])
subprocess.check_call(["%s\\run.cmd" % env_dir, "pip", "install",
                       "mozmill==%s" % (mozmill_version)])
make_relocatable("%s\\Scripts\\*.py" % (python_dir))
make_relocatable("%s\\Scripts\\hg" % (python_dir))

print "Deleting easy_install and pip scripts"
os.system("del /q %s\\Scripts\\easy_install*" % (python_dir))
os.system("del /q %s\\Scripts\\pip*" % (python_dir))

print "Deleting pre-compiled Python modules and build folder"
os.system("del /s /q %s\\*.pyc" % (python_dir))
os.system("rd /s /q %s\\build" % (env_dir))

print "Building zip archive of environment"
target_archive = os.path.join(os.path.dirname(base_dir), "win-%s" % mozmill_version)
shutil.make_archive(target_archive, "zip", env_dir)

os.system("rd /s /q %s" % (env_dir))

print "Successfully created the environment: '%s.zip'" % target_archive