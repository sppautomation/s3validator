#!/bin/bash

set -e
cd tests
../test_env/bin/pytest -v -x -s --junit-xml=test-results.xml test_partner_relation.py test_performance.py test_offload.py
