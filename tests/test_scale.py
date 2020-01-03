import json
import logging
import os
import time
import configparser
import shutil
import datetime
from prettytable import PrettyTable

import pytest

from clientcore import client

from common import system, util, consts

config = configparser.ConfigParser()
config.read("pytest.ini")
count_of_offloads = int(config.get('scale_test', 'num_of_offloads'))
base_file_size_MB = int(config.get('scale_test', 'base_file_size_MB'))
max_vsnap_streams = int(config.get('scale_test', 'max_vsnap_streams'))

analysis_offload = PrettyTable()
analysis_offload.field_names = ["Offload count", "Max streams", "Total Time ", "Total offload size", "Average offload time (sec)", "Average throughput((MB/s))" ]

@pytest.fixture(scope="module")
def setup(global_config, request):
    resources = {}
    resources['relationships'] = []
    resources['partner'] = []
    resources['shares'] = []
    resources['volumes'] = []
    resources['mountpoints'] = []
    resources['offload_sessions'] = []
    resources['total_offload_time'] = 1
    resources['start_time'] = time.time()
    resources["total_offload_size"] = 1
    request.addfinalizer(lambda: cleanup(global_config, resources))

    return resources

def cleanup(global_config, resources):
    session = global_config.session


    if resources['mountpoints']:
        for mount in resources['mountpoints']:
            util.run_silently(lambda: system.run_shell_command("umount -f {}".format(mount), use_sudo=True))

    if resources['relationships']:
        for relation in resources['relationships']:
            util.run_silently(lambda: client.VsnapAPI(session, 'relationship').delete(
                               resid=relation + "?partner_type=cloud"))

    if resources['partner']:
        util.run_silently(lambda: client.VsnapAPI(session, 'partner').delete(
                               resid=resources['partner']['id'] + "?partner_type=cloud"))

    if resources['shares']:
        for share in resources['shares']:
            util.run_silently(lambda: client.VsnapAPI(session, 'share').delete(
                               resid=share))

    if resources['volumes']:
        for volume in resources['volumes']:
            util.run_silently(lambda: client.VsnapAPI(session, 'volume').delete(
                               resid=volume + "?force=true"))

    client.VsnapAPI(session, '/api/pref').delete(
        resid="cloudMaxStreams")

    total_time = time.time() - resources['start_time']
    resources['total_offload_time'] = total_time
    avg_throughput = (resources['total_offload_size']/(1000*1000)) / int(total_time)
    avg_offload_time =  time.strftime("%H:%M:%S", time.gmtime(int(total_time) / count_of_offloads))
    size = util.get_offload_size(resources['total_offload_size'])
    resources['total_offload_time'] = time.strftime("%H:%M:%S", time.gmtime(total_time))


    analysis_offload.add_row([count_of_offloads, max_vsnap_streams,
                              resources['total_offload_time'], size,
                              avg_offload_time,
                              "{:.2f}".format(float(avg_throughput))])
    print("\n\n")
    print(analysis_offload)


def monitor_sync_session(clientsess, sync_id):
    while True:
        time.sleep(10)

        offload_session = client.VsnapAPI(clientsess, 'session').get(path=sync_id + "?partner_type=cloud")
        status = offload_session['status'];


        if status in ["COMPLETED", "FAILED"]:
            return offload_session

def get_time_in_seconds(time_string):
    h,m,s = time_string.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)

@pytest.mark.parametrize("count", range(count_of_offloads))
def test_createmulti_offloads(count, global_config, setup):
    session = global_config.session
    resources = setup

    session = global_config.session
    pool_id = global_config.pool_id
    resources['poolid'] = pool_id

 # set max streams in vsnap preference

    setpref_data = {"name": "cloudMaxStreams",
                    "value": max_vsnap_streams}

    client.VsnapAPI(session, '/api/pref').post(data=setpref_data)

    data = {"name": "vol_testoffload{}".format(count), "volume_type": "filesystem", "pool_id": pool_id}

    resources['volume'] = client.VsnapAPI(session, 'volume').post(data=data)

    resources['volumes'].append(resources['volume']['id'])

    # creating share for source volume
    sharedata = {"share_type": "nfs",
                 "share_options": {
                     "allowed_hosts": "all"
                 }}

    share = client.VsnapAPI(session, 'volume').post(path=resources['volume']['id'] + "/share", data=sharedata)
    resources['shareid'] = share['id']
    resources['shares'].append(resources['shareid'])
    share_name = share['name']

    if os.path.exists("/tmp/test_source_mountpoint{}".format(count)):
        shutil.rmtree("/tmp/test_source_mountpoint{}".format(count))
    os.makedirs("/tmp/test_source_mountpoint{}".format(count))

    serverurl = global_config.serverurl
    ip = serverurl.split("//")
    ip = ip[1]
    ip = ip.split(":")
    vsnapip = ip[0]
    resources['vsnapip'] = vsnapip

    system.run_shell_command(
        "/bin/mount -t nfs -o rw,vers=3 {}:{} /tmp/test_source_mountpoint{}".format(vsnapip, share_name, count), use_sudo=True)
    datafile = "/tmp/test_source_mountpoint{}/testbasefile1.dat".format(count)
    num_blocks = int((base_file_size_MB * consts.MB) / (64 * consts.KB))  # Using 64K as block size in dd
    system.run_shell_command("/usr/bin/dd if=/dev/urandom of={} bs=65536 count={}".format(datafile, num_blocks),
                             use_sudo=True)

    resources['mountpoints'].append('/tmp/test_source_mountpoint{}'.format(count))

    # Using env variable allows usage of a different target at run time.
    try:
        dataf = os.environ["OFFLOAD_TESTS_TARGET"]
        partnerdata = json.load(open(dataf))
    except KeyError:
        dataf = global_config.rootdir + "/config/cloud_endpoint.json"
        partnerdata = json.load(open(dataf))

    resources['partner'] = client.VsnapAPI(session, '/api/partner?partner_type=cloud').post(data=partnerdata)


    relationdata = {"partner_id": resources['partner']['id']}
    resources['relationship'] = client.VsnapAPI(session, '/api/volume').post(
        path=resources['volume']['id'] + "/relationship?partner_type=cloud", data=relationdata)

    resources['relationships'].append(resources['relationship']['id'])

    syncsess = client.VsnapAPI(session, 'api/relationship').post(
        path=resources['relationship']['id'] + "/session?partner_type=cloud", data={})

    resources['offload_sessions'].append(syncsess)
    print("\n Offload session number {} created".format(count))


@pytest.mark.parametrize("count", range(count_of_offloads))
def test_multioffload_status(count, global_config, setup):

    session = global_config.session
    resources = setup

    offload_session = monitor_sync_session(session, resources['offload_sessions'][count]['id'])
    resources['total_offload_size'] += offload_session['size_sent']

    print("\n Offload session status for session id {} is {}".format(offload_session['id'],offload_session['status']))
    if offload_session['status'] == "FAILED":
        print(offload_session['message'])

    assert offload_session['status'] == "COMPLETED"


