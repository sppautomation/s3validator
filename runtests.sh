#!/bin/bash

cd tests


if [  $1 == "functional" ]
then
../test_env/bin/pytest -v -x -s --junit-xml=test-results.xml  test_offload.py

fi

if [ $1 == "performance" ]
then
../test_env/bin/pytest -v -x -s --junit-xml=test-results.xml   test_performance.py

fi

if [ $1 == "scale" ]
then
../test_env/bin/pytest -v -x -s --junit-xml=test-results.xml test_scale.py

fi



