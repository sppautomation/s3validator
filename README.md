# s3validator


## Introduction

This directory contains tests that can be used to verify if IBM
Software cloud offload functionality works with a given S3
provider, performance analysis and scalability.

## Prerequisites

* install vSnap, these scripts need to be run on a vSnap.
* install environment to run the scripts.
..*  Run the script "install.sh" that is present in the directory.

$ ./install.sh

This will set up a Python virtual environment and will install some
dependencies that are necessary to run tests. Note that packages will
be installed into the newly created virtual environment so no changes
will be made to host's software.

* Configuring S3 Provider
..* To run tests, you need to first provide the details of the S3
provider. To do this, edit the following file:

    tests/config/cloud_endpoint.json

and provide the following information:

* endpoint. URL of the S3 provider.
* api_key. Access key to be used to login.
* api_secret. Password for the key provided above.
* bucket. Bucket name.
* provider. You can use the default value.


## Script Types

* Functional - These tests will run offload and restore using the registered s3 provider
* Performance - This test will tell us the throughput for a base offload and restore
* Scale - This test allows us to measure performance of the vSnap by varying the number of offloads it handles concurrently

## Configuring offload size

In directory tests update the pytest.ini file to set the offload size in MB's. Following are the fields you can configure, the default values are
mentioned for reference.

* Total time out (10800 seconds)

* Functional
..* Base offload (10 MB)
..* Incremental offload (5 MB)
..* Number of increments (3)


* Performance
..* Base offload size 1000 MB

* Scale
..* Base offload Size 10 MB
..* Number of offloads 10
..* Max vsnap streams 3



## Running the tests


Configure the S3 provider as described above and run the script as follows:
* Functional:
$ ./runtests.sh functional

* Performance:
$ ./runtests.sh performance

* Scale:
$ ./runtests.sh scale


The script will print information on the console as it runs each
test. Information about tests (such as APIs called and any errors) is
saved in the following two files:

* apiscalled.log
* test-results.xml

In case of any errors, please provide these files to IBM for
debugging.

