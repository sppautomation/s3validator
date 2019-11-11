#!/bin/bash

set -x
set -e

python3 -m venv test_env
./test_env/bin/pip install -r requirements.txt >/dev/null
./test_env/bin/pip install -e client >/dev/null

