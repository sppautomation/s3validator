#!/bin/bash

MYDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENVDIR="$(dirname "${MYDIR}")/s3validator_venv"
LOGDIR="$(dirname "${MYDIR}")/s3validator_logs_$(date "+%Y-%m-%dT%H-%M-%S")"

if [[ -d $LOGDIR ]]; then
	rm -rf $LOGDIR
fi

mkdir -p ${LOGDIR}

function logMsg {
	echo "$1" | tee -a ${LOGDIR}/stdout.log
}

function prepEnv {
	logMsg "$(date)"
	logMsg "Configuring vSnap environment for tests" 
	vsnap system pref set --name volumeDeleteSync --value true >>${LOGDIR}/stdout.log
	vsnap system pref set --name snapshotDeleteSync --value true >>${LOGDIR}/stdout.log
	vsnap system pref set --name cloudTrimMonitorNumAttempts --value 3 >>${LOGDIR}/stdout.log
}

function clearEnv {
	logMsg "$(date)"
	logMsg "Resetting vSnap environment"
	vsnap system pref clear --name volumeDeleteSync >>${LOGDIR}/stdout.log
	vsnap system pref clear --name snapshotDeleteSync >>${LOGDIR}/stdout.log
	vsnap system pref clear --name cloudTrimMonitorNumAttempts >>${LOGDIR}/stdout.log
}

logMsg
logMsg "Starting test run"
logMsg "Logs will be written under: $LOGDIR"

cd $MYDIR/tests

if [[ $1 == "functional" ]]; then
	prepEnv
	$VENVDIR/bin/pytest -v -x -s --junit-xml=${LOGDIR}/test-results.xml test_offload.py | tee -a ${LOGDIR}/stdout.log
	clearEnv
elif [[ $1 == "performance" ]]; then
	prepEnv
	$VENVDIR/bin/pytest -v -x -s --junit-xml=${LOGDIR}/test-results.xml test_performance.py | tee -a ${LOGDIR}/stdout.log
	clearEnv
elif [[ $1 == "scale" ]]; then
	prepEnv
	$VENVDIR/bin/pytest -v -x -s --junit-xml=${LOGDIR}/test-results.xml test_scale.py | tee -a ${LOGDIR}/stdout.log
	clearEnv
else
	logMsg
	logMsg "ERROR: Invalid test type specified: $1"
fi

