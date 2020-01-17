import json
import logging
import os
import time
import configparser
import shutil
import tempfile
import conftest

import pytest

from clientcore import client

from common import system, util, consts

config = configparser.ConfigParser()
config.read("pytest.ini")
incr_count = int(config.get('offload_test', 'incr_count'))
base_file_size_MB = int(config.get('offload_test', 'base_file_size_MB'))
incr_file_size_MB = int(config.get('offload_test', 'incr_file_size_MB'))


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


        if status in ["COMPLETED", "FAILED"]:
           return offload_session


def restore(offload_session, resources, global_config, filename, vol_name):
    session = global_config.session
    data = {"name": vol_name,
            "snapshot_id": offload_session['snap_version']}
    resources['snapshots'].append(offload_session['snap_version'])
    try:
        restore_session = client.VsnapAPI(session, 'api/partner').post(
            path=offload_session['partner_id'] + "/volume", data=data)


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


    finally:

        util.run_silently(
            lambda: system.run_shell_command("/bin/umount -f /tmp/test_restore_mountpoint", use_sudo=True))

        util.run_silently(
            lambda: client.VsnapAPI(session, 'api/partner/' + resources['partner']['id'] + '/share').delete(
                resid=share['id']))

        util.run_silently(
            lambda: client.VsnapAPI(session, 'api/partner/' + resources['partner']['id'] + '/volume').delete(
                resid=restore_vol_id))

def alternate_restore(offload_session, resources, global_config, filename, vol_name):
    session = global_config.session
    data = {"name": vol_name,
            "snapshot_id": offload_session['snap_version']}
    resources['snapshots'].append(offload_session['snap_version'])
    try:

        # adding partner to alternate vnap
        alt_session = client.VsnapSession('https://172.20.3.136:8900', 'vsnap', 'YKojGy3mBmRh')
        conftest.vsnap_init(alt_session)
        resp = client.VsnapAPI(alt_session, 'pool').get()
        alt_pool_id = resp['pools'][0]['id']

        try:
            dataf = os.environ["OFFLOAD_TESTS_TARGET"]
            partnerdata = json.load(open(dataf))
        except KeyError:
            dataf = global_config.rootdir + "/config/cos.json"
            partnerdata = json.load(open(dataf))

        resources['alt_partner'] = client.VsnapAPI(alt_session, '/api/partner?partner_type=cloud').post(data=partnerdata)

        resp = client.VsnapAPI(alt_session, 'api/partner').get(path='{}/volume/{}'.format(resources['alt_partner']['id'], resources['relationship']['remote_vol_id']))

        restore_session = client.VsnapAPI(alt_session, 'api/partner').post(
            path=resources['alt_partner']['id'] + "/volume", data=data)


        # operation on alternate vsnap ended
        restore_session = monitor_sync_session(alt_session, restore_session['id'])
        assert restore_session['status'] == "COMPLETED"
        restore_vol_id = restore_session['clone_vol_id']

        # create restore share
        sharedata = {"share_type": "nfs",
                     "share_options": {
                         "allowed_hosts": ['all']
                     }}
        share = client.VsnapAPI(alt_session, '/api/partner').post(
            path="{}/volume/{}/share".format(resources['alt_partner']['id'], restore_vol_id), data=sharedata)
        share_name = share['name']

        if os.path.exists("/tmp/test_restore_mountpoint"):
            shutil.rmtree("/tmp/test_restore_mountpoint")
        os.makedirs("/tmp/test_restore_mountpoint")

        system.run_shell_command(
            "/bin/mount -t nfs -o rw,vers=3 {}:{} /tmp/test_restore_mountpoint".format('172.20.3.136',
                                                                                       share_name), use_sudo=True)
        arestore = "/tmp/test_restore_mountpoint/{}".format(filename)
        brestore = "/tmp/test_source_mountpoint/{}".format(filename)
        system.run_shell_command("cmp {} {}".format(brestore, arestore), use_sudo=True)



    finally:

        util.run_silently(
            lambda: system.run_shell_command("/bin/umount -f /tmp/test_restore_mountpoint", use_sudo=True))

        util.run_silently(
            lambda: client.VsnapAPI(alt_session, 'api/partner/' + resources['alt_partner']['id'] + '/share').delete(
                resid=share['id']))

        util.run_silently(
            lambda: client.VsnapAPI(alt_session, 'api/partner/' + resources['alt_partner']['id'] + '/volume').delete(
                resid=restore_vol_id))


def cancel_offload(session, resources):
    datafile = "/tmp/test_source_mountpoint/testfile1.dat"
    num_blocks = int((200 * consts.MB) / (64 * consts.KB))  # Using 64K as block size in dd
    system.run_shell_command("/usr/bin/dd if=/dev/urandom of={} bs=65536 count={}".format(datafile, num_blocks), use_sudo=True)

    syncsess = client.VsnapAPI(session, 'relationship').post(
        path=resources['relationship']['id'] + "/session?partner_type=cloud", data={})

    while True:
        offload_session = client.VsnapAPI(session, 'session').get(path=syncsess['id'] + "?partner_type=cloud")
        if offload_session['status'] in ['COMPLETED', 'FAILED'] or (offload_session['status'] == 'ACTIVE' and offload_session['size_sent'] > 0):
            break

    if (offload_session['status'] != 'ACTIVE'):
        assert False, "Cancel offload test failed because partner session is not active."

    # cancel offload
    client.VsnapAPI(session, '/api/partner').post(
        path=resources['partner']['id'] + "/session/" + syncsess['id'] , data={"action":"cancel"})
    offload_session = monitor_sync_session(session, syncsess['id'])

    assert offload_session['is_cancelled']
    assert offload_session['status'] == "FAILED"


@pytest.mark.dependency()
def test_base_offload(global_config, setup):

    session = global_config.session
    resources = setup

    syncsess = client.VsnapAPI(session, 'relationship').post(
        path=resources['relationship']['id'] + "/session?partner_type=cloud", data={})


    offload_session = monitor_sync_session(session, syncsess['id'])
    resources['base_offload_session'] = offload_session
    assert offload_session['status'] == "COMPLETED"

    restore(offload_session, resources, global_config, "testbasefile1.dat", "vol_base_offload")


@pytest.mark.dependency(name="test_incr_offload", depends=['test_base_offload'])
@pytest.mark.parametrize("path", range(incr_count))
def test_incr_offload(path, global_config, setup):
    session = global_config.session
    resources = setup

    datafile = "/tmp/test_source_mountpoint/testincrfile{}.dat".format(path + 2)
    filename = "testincrfile{}.dat".format(path + 2)
    num_blocks = int((incr_file_size_MB * consts.MB) / (64 * consts.KB))  # Using 64K as block size in dd
    system.run_shell_command("/usr/bin/dd if=/dev/urandom of={} bs=65536 count={}".format(datafile, num_blocks), use_sudo=True)

    syncsess = client.VsnapAPI(session, 'relationship').post(
        path=resources['relationship']['id'] + "/session?partner_type=cloud", data={})


    offload_session = monitor_sync_session(session, syncsess['id'])
    if (path == 1):
        resources['incr_filename'] = "testincrfile{}.dat".format(path + 2)
        resources['incr_offload_session'] = offload_session

    assert offload_session['status'] == "COMPLETED"
    restore(offload_session, resources, global_config, filename, "vol_incr_offload_{}".format(path + 2))


def _test_cancel_base_offload(global_config, setup):
    session = global_config.session
    resources = setup
    cancel_offload(session, resources)


@pytest.mark.dependency(depends=['test_base_offload'])
def _test_cancel_incr_offload(global_config, setup):
    session = global_config.session
    resources = setup
    cancel_offload(session, resources)



