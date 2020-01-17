#!/bin/bash

MYDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENVDIR=${MYDIR}_venv

cd $MYDIR/tests

if [  $1 == "functional" ]
then
	$VENVDIR/bin/pytest -v -x -s --junit-xml=test-results.xml  test_offload.py
fi

if [ $1 == "performance" ]
then
	$VENVDIR/bin/pytest -v -x -s  --serverurl=$2 --junit-xml=test-results.xml  test_performance.py
fi

if [ $1 == "scale" ]
then
	$VENVDIR/bin/pytest -v -x -s  --junit-xml=test-results.xml test_scale.py
fi
