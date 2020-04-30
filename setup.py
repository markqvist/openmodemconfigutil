import os
from setuptools import setup

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
