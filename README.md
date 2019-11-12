# s3validator


## Introduction

This directory contains tests that can be used to verify if IBM
Software cloud offload functionality works with a given S3
provider.

The tests need to be run on a vSnap.

## Installation

Run the script "install.sh" that is present in the directory.

$ ./install.sh

This will set up a Python virtual environment and will install some
dependencies that are necessary to run tests. Note that packages will
be installed into the newly created virtual environment so no changes
will be made to host's software.

## Configuring S3 Provider

To run tests, you need to first provide the details of the S3
provider. To do this, edit the following file:

    tests/config/cloud_endpoint.json

and provide the following information:

* endpoint. URL of the S3 provider.
* api_key. Access key to be used to login.
* api_secret. Password for the key provided above.
* bucket. Bucket name.

There is an additional field in the JSON file called "provider". You
can leave it as is.

## Configuring offload size

In directory tests update the pytest.ini file to set the offload size in MB's.

Default values are as follows:

* Base offload 10 MB
* Incremental offload 5 MB
* Number of increments 3
* Total time out 10800 seconds


## Running the tests


Configure the S3 provider as described above and run the script
"runtests.sh". This will run all the tests available

$ ./runtests.sh

The script will print information on the console as it runs each
test. Information about tests (such as APIs called and any errors) is
saved in the following two files:

* apiscalled.log
* test-results.xml

In case of any errors, please provide these files to IBM for
debugging.

