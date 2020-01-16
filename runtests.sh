#!/bin/bash

MYDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENVDIR=${MYDIR}_venv
LOGDIR=${MYDIR}_logs_$(date "+%Y-%m-%dT%H-%M-%S")

if [[ -d $LOGDIR ]]; then
	rm -rf $LOGDIR
fi

function logMsg {
	echo "$1" | tee -a ${LOGDIR}/stdout.log
}

logMsg
logMsg "Starting test run"
logMsg "Logs will be written under: $LOGDIR"

logMsg
logMsg "Configuring vSnap environment for tests"
vsnap system pref set --name volumeDeleteSync --value true
vsnap system pref set --name snapshotDeleteSync --value true
vsnap system pref set --name cloudTrimMonitorNumAttempts --value 3

cd $MYDIR/tests

if [  $1 == "functional" ]; then
	$VENVDIR/bin/pytest -v -x -s --junit-xml=${LOGDIR}/test-results.xml test_offload.py | tee -a ${LOGDIR}/stdout.log
elif [ $1 == "performance" ]; then
	$VENVDIR/bin/pytest -v -x -s --junit-xml=${LOGDIR}/test-results.xml test_performance.py | tee -a ${LOGDIR}/stdout.log
elif [ $1 == "scale" ]; then
	$VENVDIR/bin/pytest -v -x -s --junit-xml=${LOGDIR}/test-results.xml test_scale.py | tee -a ${LOGDIR}/stdout.log
else
	logMsg
	logMsg "Invalid test type specified: $1"
fi
