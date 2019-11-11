import json
import logging
import os
import time
import configparser
import shutil
import tempfile

import pytest

from clientcore import client

from common import system, util, consts


@pytest.fixture(scope="module")
def setup(global_config, request):
    resources = {}
    request.addfinalizer(lambda: cleanup(global_config, resources))
    session = global_config.session
    pool_id = global_config.pool_id
    resources['poolid'] = pool_id

    data = {"name": "vol_crud", "volume_type": "filesystem", "pool_id": pool_id}

    resources['volume'] = client.VsnapAPI(session, 'volume').post(data=data)

    return resources


def cleanup(global_config, resources):
    session = global_config.session

    util.run_silently_pred(resources.get('partner', None),lambda : client.VsnapAPI(session, 'partner').delete(resid=resources['partner']['id'] +"?partner_type=cloud"))

    util.run_silently_pred(resources.get("volume", None),
                           lambda: client.VsnapAPI(session, 'volume').delete(
                               resid=resources['volume']["id"]))

@pytest.mark.dependency()
def test_create_partner(global_config, setup):
    session = global_config.session
    resources = setup

    try:
        dataf = os.environ["OFFLOAD_TESTS_TARGET"]
        partnerdata = json.load(open(dataf))
    except KeyError:
        dataf = global_config.rootdir + "/config/cloud_endpoint.json"
        partnerdata = json.load(open(dataf))

    resources['partner'] = client.VsnapAPI(session, '/api/partner?partner_type=cloud').post(data=partnerdata)
    assert resources['partner']['id'] != None


@pytest.mark.dependency(depends = ['test_create_partner'])
def test_get_partner_by_id(global_config,setup):
    session = global_config.session
    resources = setup

    partnerid = resources['partner']['id']
    getid = client.VsnapAPI(session, 'partner').get(path="{}?partner_type=cloud".format(partnerid))['id']

    assert partnerid == getid

@pytest.mark.dependency(depends = ['test_create_partner'])
def test_create_relationship(global_config, setup):
    session = global_config.session
    resources = setup

    relationdata = {"partner_id": resources['partner']['id']}
    resources['relationship'] = client.VsnapAPI(session, '/api/volume').post(
        path=resources['volume']['id'] + "/relationship?partner_type=cloud", data=relationdata)
    resources['remote_volume'] = resources['relationship']['remote_vol_id']
    assert resources['relationship']['id'] != None


@pytest.mark.dependency(depends = ['test_create_relationship'])
def test_get_relationship_by_id(global_config,setup):
    session = global_config.session
    resources = setup

    relationid = resources['relationship']['id']
    getid = client.VsnapAPI(session, 'relationship').get(path="{}?partner_type=cloud".format(relationid))['id']

    assert relationid == getid


@pytest.mark.dependency(depends = ['test_create_relationship'])
def test_remove_relationship(global_config,setup):
    session = global_config.session
    resources = setup

    resp = client.VsnapAPI(session, 'relationship').delete(resid=resources['relationship']['id'] +"?partner_type=cloud")
    assert resp == {}

@pytest.mark.dependency(depends = ['test_create_partner'])
def test_remove_partner(global_config,setup):
    session = global_config.session
    resources = setup
    resp = client.VsnapAPI(session, 'partner').delete(resid=resources['partner']["id"] +"?partner_type=cloud")
    assert resp == {}

























