#!/usr/bin/env bash

pushd ..

git clone 'https://github.com/fastily/pwiki.git'
pip install -e pwiki --config-settings editable_mode=strict

popd

pip install -r "requirements-dev.txt"