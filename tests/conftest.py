
import logging
import os
import time

import pytest
import requests

from _pytest.runner import  runtestprotocol

from clientcore import client

def init_logging():
    logger = logging.getLogger()
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(''))
    logger.addHandler(ch)

def pytest_addoption(parser):
    parser.addoption("--serverurl", action="store", default="https://localhost:8900",
                     help="vSnap server url")
    parser.addoption("--username", action="store", default="vsnap",
                     help="vSnap username")
    parser.addoption("--password", action="store", default="YKojGy3mBmRh",
                     help="vSnap password")

def pytest_configure(config):
    os.environ["serverurl"] = config.getoption('serverurl')
    os.environ["username"] = config.getoption('username')
    os.environ["password"] = config.getoption('password')

def raise_response_error(r, *args, **kwargs):
    r.raise_for_status()

class BdgGateway:
    def __init__(self):
        self.url = "http://localhost:8000/devices"

        self.client = requests.Session()
        self.client.hooks.update({'response': raise_response_error})

class GlobalConfig:
    def __init__(self, session, rootdir, serverurl, username, password, pool_id):
        self.session = session
        self.rootdir = rootdir
        self.serverurl = serverurl
        self.username = username
        self.password = password
        self.pool_id = pool_id


        self.gateway = BdgGateway()

def vsnap_init(session):
    status = client.VsnapAPI(session, 'system').get()['init_status']

    if status != "Ready":
        data = {"action": "init", "async": True, "multipool": False, "skip_pool": False}
        client.VsnapAPI(session, 'system').post(data=data)

        count = 0
        while True:
            time.sleep(30)
            status = client.VsnapAPI(session, 'system').get()['init_status']

            if status != "Initializing":
                break
    
            count += 1
            if count > 40:
                break

        if status != "Ready":
            raise Exception("Initialization failed with status:{}".format(status) )

@pytest.fixture(scope = "session")
def global_config(pytestconfig):
    init_logging()
    serverurl = os.getenv('serverurl')
    username = os.getenv('username')
    password = os.getenv('password')
    session = client.VsnapSession(os.getenv('serverurl'), os.getenv('username'), os.getenv('password'))
    vsnap_init(session)
    resp = client.VsnapAPI(session, 'pool').get()
    pool_id = resp['pools'][0]['id']

    return GlobalConfig(session, str(pytestconfig.rootdir), serverurl, username, password, pool_id)

# def pytest_runtest_protocol(item, nextitem):
#     reports = runtestprotocol(item, nextitem=nextitem)
#     for report in reports:
#         if report.when == 'call':
#             logging.info('\n')
#             logging.info('(Above are API calls for test:{})#######################'.format(item.name))
#     return True








