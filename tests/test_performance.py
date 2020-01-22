import json
import logging
import os
import time
import configparser
import shutil
import datetime
import tempfile
import conftest
from prettytable import PrettyTable

import pytest

from clientcore import client

from common import system, util, consts

config = configparser.ConfigParser()
config.read("pytest.ini")
base_file_size_MB = int(config.get('performance_test', 'base_file_size_MB'))

def title_txt(txt): print('\x1b[5;30;42m' + txt + '\x1b[0m')

analysis_offload = PrettyTable()
analysis_restore = PrettyTable()
analysis_offload.field_names = ["Job Type", "Time taken", "Throughput (MB/s)", "Size"]
analysis_restore.field_names = ["Job Type", "Time taken", "Size", "Throughput (MB/s)"]

@pytest.fixture(scope="module")
def setup(global_config, request):
    resources = {}
    resources['snapshots'] = []
    resources['delete_partner'] = True
    request.addfinalizer(lambda: cleanup(global_config, resources))
    session = global_config.session
    pool_id = global_config.pool_id
    resources['poolid'] = pool_id

    data = {"name": "vol_testoffload", "volume_type": "filesystem", "pool_id": pool_id}

    resources['volume'] = client.VsnapAPI(session, 'volume').post(data=data)

    # creating share for source volume
    sharedata = {"share_type": "nfs",
                 "share_options": {
                     "allowed_hosts": "all"
                 }}

    share = client.VsnapAPI(session, 'volume').post(path=resources['volume']['id'] + "/share", data=sharedata)
    resources['shareid'] = share['id']
    share_name = share['name']
    resources['share_id'] = share['id']


    if os.path.exists("/tmp/test_source_mountpoint"):
        shutil.rmtree("/tmp/test_source_mountpoint")
    os.makedirs("/tmp/test_source_mountpoint")

    serverurl = global_config.serverurl
    ip = serverurl.split("//")
    ip = ip[1]
    ip = ip.split(":")
    vsnapip = ip[0]
    resources['vsnapip'] = vsnapip


    system.run_shell_command(
        "/bin/mount -t nfs -o rw,vers=3 {}:{} /tmp/test_source_mountpoint".format(vsnapip, share_name), use_sudo=True)
    datafile = "/tmp/test_source_mountpoint/testbasefile1.dat"
    num_blocks = int((base_file_size_MB * consts.MB) / (64 * consts.KB))  # Using 64K as block size in dd
    system.run_shell_command("/usr/bin/dd if=/dev/urandom of={} bs=65536 count={}".format(datafile, num_blocks), use_sudo=True)

    # Using env variable allows usage of a different target at run time.
    try:
        dataf = os.environ["OFFLOAD_TESTS_TARGET"]
        partnerdata = json.load(open(dataf))
    except KeyError:
        dataf = global_config.rootdir + "/config/cloud_endpoint.json"
        partnerdata = json.load(open(dataf))

    exisiting_partners = client.VsnapAPI(session, '/api/partner?partner_type=cloud').get()['partners']
    for partner in exisiting_partners:
        if partner['endpoint'] == partnerdata['endpoint']:
            resources['delete_partner'] = False

    resources['partner'] = client.VsnapAPI(session, '/api/partner?partner_type=cloud').post(data=partnerdata)

    relationdata = {"partner_id": resources['partner']['id']}
    resources['relationship'] = client.VsnapAPI(session, '/api/volume').post(
        path=resources['volume']['id'] + "/relationship?partner_type=cloud", data=relationdata)

    return resources


def cleanup(global_config, resources):
    session = global_config.session

    util.run_silently(lambda: system.run_shell_command("umount -f /tmp/test_source_mountpoint", use_sudo=True))

    util.run_silently_pred(resources.get("relationship", None),
                           lambda: client.VsnapAPI(session, 'relationship').delete(
                               resid=resources['relationship']["id"] + "?partner_type=cloud"))
    if resources['snapshots']:
        for snap in resources['snapshots']:
            util.run_silently(lambda: client.VsnapAPI(session, 'api/partner/' + resources['partner']['id'] + '/snapshot').delete(
                resid=snap))

    if resources['delete_partner']:
        util.run_silently_pred(resources.get("partner", None),
                           lambda: client.VsnapAPI(session, 'partner').delete(
                               resid=resources['partner']["id"] + "?partner_type=cloud"))

    util.run_silently_pred(resources.get("shareid", None),
                           lambda: client.VsnapAPI(session, 'share').delete(
                               resid=resources['shareid']))

    util.run_silently_pred(resources.get("volume", None),
                           lambda: client.VsnapAPI(session, 'volume').delete(
                               resid=resources['volume']["id"] + "?force=true"))

def monitor_sync_session(clientsess, sync_id):
    while True:
        time.sleep(10)

        offload_session = client.VsnapAPI(clientsess, 'session').get(path=sync_id + "?partner_type=cloud")
        status = offload_session['status'];
        # print("Session details: {}".format(offload_session))

        if status in ["COMPLETED", "FAILED"]:
            if offload_session['action'] == 'upload':
                size = util.get_offload_size(offload_session['size_sent'])

                print("\n")
                title_txt("UPLOAD:")

                time_taken = int(offload_session['time_ended']) - int(offload_session['time_started'])
                t = str(datetime.timedelta(seconds=time_taken))
                throughput = str(round(offload_session['size_sent'] / time_taken, 2))

                analysis_offload.add_row(["Upload", "{} (hh:mm:ss)".format(t), throughput, size])
                print(analysis_offload)
            return offload_session


def restore(offload_session, resources, global_config, filename, vol_name):
    session = global_config.session
    data = {"name": vol_name,
            "snapshot_id": offload_session['snap_version']}
    resources['snapshots'].append(offload_session['snap_version'])
    try:
        restore_session = client.VsnapAPI(session, 'api/partner').post(
            path=offload_session['partner_id'] + "/volume", data=data)

        # print('Restore session id is {}'.format(restore_session['id']))
        restore_session = monitor_sync_session(session, restore_session['id'])
        assert restore_session['status'] == "COMPLETED"
        restore_vol_id = restore_session['clone_vol_id']

        # create restore share
        sharedata = {"share_type": "nfs",
                     "share_options": {
                         "allowed_hosts": "all"
                     }}
        share = client.VsnapAPI(session, '/api/partner').post(
            path="{}/volume/{}/share".format(resources['partner']['id'], restore_vol_id), data=sharedata)
        share_name = share['name']

        if os.path.exists("/tmp/test_restore_mountpoint"):
            shutil.rmtree("/tmp/test_restore_mountpoint")
        os.makedirs("/tmp/test_restore_mountpoint")

        system.run_shell_command(
            "/bin/mount -t nfs -o rw,vers=3 {}:{} /tmp/test_restore_mountpoint".format(resources['vsnapip'],
                                                                                       share_name), use_sudo=True)
        arestore = "/tmp/test_restore_mountpoint/{}".format(filename)
        brestore = "/tmp/test_source_mountpoint/{}".format(filename)
        system.run_shell_command("cmp {} {}".format(brestore, arestore), use_sudo=True)

        #run scrub command if running locally
        if global_config.serverurl == "https://localhost:8900":
            rpool = "rpool"+ restore_session['clone_vol_id']
            system.run_shell_command("zpool scrub {}".format(rpool), use_sudo=True)

        #read and write after restore
        datafile = "/tmp/test_restore_mountpoint/testing1.dat"
        num_blocks = int((base_file_size_MB * consts.MB) / (64 * consts.KB))  # Using 64K as block size in dd
        system.run_shell_command("/usr/bin/dd if=/dev/urandom of={} bs=65536 count={}".format(datafile, num_blocks),
                                 use_sudo=True)
        testing1 = "/tmp/test_restore_mountpoint/testing1.dat"
        system.run_shell_command("cp {} {}".format("/tmp/test_restore_mountpoint/testing1.dat", "/tmp/test_restore_mountpoint/testing2.dat"), use_sudo=True)
        testing2 = "/tmp/test_restore_mountpoint/testing2.dat"
        system.run_shell_command("cmp {} {}".format(testing1, testing2), use_sudo=True)

        # time taken to write restored file

        start_time = time.time()
        system.run_shell_command("/usr/bin/dd if=/tmp/test_restore_mountpoint/{} of=/dev/null".format(filename),
                                 use_sudo=True)
        elapsed_restore_time = time.time() - start_time
        t = str(datetime.timedelta(seconds=elapsed_restore_time))
        size = util.get_offload_size(base_file_size_MB * 1000 * 1000)
        throughput = str(round(base_file_size_MB / elapsed_restore_time, 2))

        print("\n")
        title_txt("RESTORE:")

        analysis_restore.add_row(["Restore", "{} (hh:mm:ss)".format(t), size, throughput])
        print(analysis_restore)


    finally:

        util.run_silently(
            lambda: system.run_shell_command("/bin/umount -f /tmp/test_restore_mountpoint", use_sudo=True))

        util.run_silently(
            lambda: client.VsnapAPI(session, 'api/partner/' + resources['partner']['id'] + '/share').delete(
                resid=share['id']))

        util.run_silently(
            lambda: client.VsnapAPI(session, 'api/partner/' + resources['partner']['id'] + '/volume').delete(
                resid=restore_vol_id))


@pytest.mark.dependency()
def test_base_offload(global_config, setup):

    session = global_config.session
    resources = setup

    syncsess = client.VsnapAPI(session, 'relationship').post(
        path=resources['relationship']['id'] + "/session?partner_type=cloud", data={})

    # print("Session id for base offload {}".format(syncsess['id']))
    offload_session = monitor_sync_session(session, syncsess['id'])
    resources['base_offload_session'] = offload_session
    assert offload_session['status'] == "COMPLETED"

    restore(offload_session, resources, global_config, "testbasefile1.dat", "vol_base_offload")


