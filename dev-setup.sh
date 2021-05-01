#!/usr/bin/env bash

pushd ..

git clone 'https://github.com/fastily/pwiki.git'
pip install -e pwiki

popd

pip install -r "requirements-dev.txt"