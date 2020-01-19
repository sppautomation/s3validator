#!/bin/bash

set -e

MYDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENVDIR="$(dirname "${MYDIR}")/s3validator_venv"

echo
echo "Creating virtual environment under: $VENVDIR"

if [[ -d $VENVDIR ]]; then
	echo "Detected an older virtual environment, deleting it and creating a new one"
	rm -rf $VENVDIR
fi

echo "Installing dependencies"
echo

python3 -m venv $VENVDIR
$VENVDIR/bin/pip install -r $MYDIR/requirements.txt
$VENVDIR/bin/pip install -e $MYDIR/client

echo
echo "Installation complete"