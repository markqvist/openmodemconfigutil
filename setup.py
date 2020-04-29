import os
from setuptools import setup

def tree(src):
    return [(root, map(lambda f: os.path.join(root, f), files))
        for (root, dirs, files) in os.walk(os.path.normpath(src))]

APP = ['openmodemconfig.py']
DATA_FILES = []
OPTIONS = {'argv_emulation': False,
		   'includes': ['WebKit', 'Foundation', 'webview'],
		   'iconfile': 'gfx/AppIcon.icns',
		   }

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
