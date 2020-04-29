#!/bin/bash
find . -type f -name "*.py[co]" -delete
find . -type d -name "__pycache__" -delete
rm -r ./build
rm -r ./dist

python3 setup.py py2app
cp -rv ./public ./dist/openmodemconfig.app/Contents/Resources/
mv ./dist/openmodemconfig.app ./dist/OpenModem\ Config.app
