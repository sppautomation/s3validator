import json
import logging
import os
import re
import tempfile
import time
import pprint

from xml.sax.saxutils import unescape


import requests
from requests.auth import HTTPBasicAuth

try:
    import urllib3
except ImportError:
    from requests.packages import urllib3

try:
    import http.client as http_client
except ImportError:
    # Python 2
    import httplib as http_client

# http_client.HTTPConnection.debuglevel = 1
urllib3.disable_warnings()

resource_to_endpoint = {
    'system': '/api/system',
    'volume': '/api/volume',
    'snapshot': '/api/snapshot',
    'pool': '/api/pool',
    'network': '/api/network',
    'partner': '/api/partner',
    'relationship': '/api/relationship',
    'session': '/api/session',
    'share': '/api/share',
    'pref': '/api/pref'
}

resource_to_listfield = {
    'identityuser': 'users',
    'identitycredential': 'users',
    'policy': 'policies',
    'ldap': 'ldapServers',
    'pure': 'purestorages',
    'workflow': 'storageprofiles',
    'resourcepool': 'resourcePools',
}


def build_url(baseurl, restype=None, resid=None, path=None, endpoint=None):
    url = baseurl

    if restype is not None:
        ep = resource_to_endpoint.get(restype, None)
        if not ep:
            if endpoint is not None:
                ep = endpoint
            else:
                ep = restype

        url = url + "/" + ep

    if resid is not None:
        url = url + "/" + str(resid)

    if path is not None:
        if not path.startswith('/'):
            path = '/' + path
        url = url + path

    return url.replace("/api/ngp", "/ngp")


def raise_response_error(r, *args, **kwargs):
    '''
    if r.content:
        try:
            pretty_print(r.json())
        except:
            print(r.content)
            '''
    r.raise_for_status()


def pretty_print(data):
    return logging.info(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))


class VsnapSession(object):
    def __init__(self, url, username=None, password=None, sessionid=None):
        self.url = url
        self.sess_url = url + '/api'
        self.api_url = url + ''
        self.username = username
        self.password = password
        self.sessionid = sessionid

        self.conn = requests.Session()
        self.conn.verify = False
        self.conn.hooks.update({'response': raise_response_error})
        self.conn.headers.update({'Content-Type': 'application/json'})
        self.conn.headers.update({'Accept': 'application/json'})

    def login(self):
        r = self.conn.post("%s/endeavour/session" % self.sess_url, auth=HTTPBasicAuth(self.username, self.password))
        self.sessionid = r.json()['sessionid']

    def __repr__(self):
        return 'VsnapSession: user: %s' % self.username

    def get(self, restype=None, resid=None, path=None, params={}, endpoint=None, url=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        logging.info('\n\n')
        logging.info('GET  {}'.format(url))

        # return json.loads(self.conn.get(url, params=params).content)
        response = self.conn.get(url, params=params, auth=HTTPBasicAuth(self.username, self.password))

        logging.info("{} {}".format(response.status_code, requests.status_codes._codes[response.status_code][0]))
        logging.info('\n')
        if response.content:
            response_json = response.json()
            logging.info('\n')
            logging.info(json.dumps(response_json, sort_keys=True, indent=4, separators=(',', ': ')))

        return response_json if response.content else None

    def stream_get(self, restype=None, resid=None, path=None, params={}, endpoint=None, url=None, outfile=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        r = self.conn.get(url, params=params, auth=HTTPBasicAuth(self.username, self.password))
        # logging.info("headers: %s" % r.headers)

        # The response header Content-Disposition contains default file name
        #   Content-Disposition: attachment; filename=log_1490030341274.zip
        default_filename = re.findall('filename=(.+)', r.headers['Content-Disposition'])[0]

        if not outfile:
            if not default_filename:
                raise Exception("Couldn't get the file name to save the contents.")

            outfile = os.path.join(tempfile.mkdtemp(), default_filename)

        with open(outfile, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                fd.write(chunk)

        return outfile

    def delete(self, restype=None, resid=None, path=None, params={}, endpoint=None, url=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        logging.info('\n\n')
        logging.info('API Request:DELETE')
        logging.info('\n')
        logging.info('Request Body: {}'.format(url))

        response = self.conn.delete(url, params=params, auth=HTTPBasicAuth(self.username, self.password))
        logging.info("{} {}".format(response.status_code, requests.status_codes._codes[response.status_code][0]))
        logging.info('\n')
        if response.content:
            response_json = response.json()
            logging.info('\n')
            logging.info(json.dumps(response_json, sort_keys=True, indent=4, separators=(',', ': ')))

        # return json.loads(resp.content) if resp.content else None
        return response_json if response.content else None

    def post(self, restype=None, resid=None, path=None, data={}, params={}, endpoint=None, url=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)


        logging.info('\n\n')
        logging.info('API Request:POST')
        logging.info('\n')
        logging.info('Request Body: {}'.format(url))
        response = self.conn.post(url, json=data, params=params, auth=HTTPBasicAuth(self.username, self.password))
        logging.info("{} {}".format(response.status_code, requests.status_codes._codes[response.status_code][0]))
        logging.info('\n')
        if response.content:
            response_json = response.json()
            logging.info('\n')
            logging.info(json.dumps(response_json, sort_keys=True, indent=4, separators=(',', ': ')))

        # return json.loads(resp.content) if resp.content else None
        return response_json if response.content else None


    def put(self, restype=None, resid=None, path=None, data={}, params={}, endpoint=None, url=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        # logging.info(json.dumps(data, indent=4)
        logging.info('\n\n')
        logging.info('API Request:PUT')
        logging.info('\n')
        logging.info('Request Body: {}'.format(url))
        r = self.conn.put(url, json=data, params=params, auth=HTTPBasicAuth(self.username, self.password))

        response_json = response.json()
        logging.info("{} {}".format(response.status_code, requests.status_codes._codes[response.status_code][0]))
        logging.info('\n')
        if response.content:
            response_json = response.json()
            logging.info('\n')
            logging.info(json.dumps(response_json, sort_keys=True, indent=4, separators=(',', ': ')))

        # return json.loads(resp.content) if resp.content else None
        return response_json if response.content else None


class VsnapWithSession(object):
    def __init__(self, url, username=None, password=None, sessionid=None):
        self.url = url
        self.sess_url = url + '/api/auth'
        self.api_url = url + ''
        self.username = username
        self.password = password
        self.sessionid = sessionid

        self.conn = requests.Session()
        self.conn.verify = False
        self.conn.hooks.update({'response': raise_response_error})

        if not self.sessionid:
            if self.username and self.password:
                self.login()
            else:
                raise Exception('Please provide login credentials.')

        self.conn.headers.update({'x-sessionid': self.sessionid})
        self.conn.headers.update({'Content-Type': 'application/json'})
        self.conn.headers.update({'Accept': 'application/json'})

    def login(self):
        r = self.conn.post("%s" % self.sess_url, auth=HTTPBasicAuth(self.username, self.password))
        self.sessionid = r.json()['session_id']

    def __repr__(self):
        return 'VsnapSession: user: %s' % self.username

    def get(self, restype=None, resid=None, path=None, params={}, endpoint=None, url=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        # return json.loads(self.conn.get(url, params=params).content)
        return self.conn.get(url, params=params).json()

    def stream_get(self, restype=None, resid=None, path=None, params={}, endpoint=None, url=None, outfile=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        r = self.conn.get(url, params=params)
        # logging.info("headers: %s" % r.headers)

        # The response header Content-Disposition contains default file name
        #   Content-Disposition: attachment; filename=log_1490030341274.zip
        default_filename = re.findall('filename=(.+)', r.headers['Content-Disposition'])[0]

        if not outfile:
            if not default_filename:
                raise Exception("Couldn't get the file name to save the contents.")

            outfile = os.path.join(tempfile.mkdtemp(), default_filename)

        with open(outfile, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                fd.write(chunk)

        return outfile

    def delete(self, restype=None, resid=None, path=None, params={}, endpoint=None, url=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        resp = self.conn.delete(url, params=params)

        # return json.loads(resp.content) if resp.content else None
        return resp.json() if resp.content else None

    def post(self, restype=None, resid=None, path=None, data={}, params={}, endpoint=None, url=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        # logging.info(json.dumps(data, indent=4))
        r = self.conn.post(url, json=data, params=params)

        if r.content:
            return r.json()

        return {}

    def put(self, restype=None, resid=None, path=None, data={}, params={}, endpoint=None, url=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        # logging.info(json.dumps(data, indent=4))
        r = self.conn.put(url, json=data, params=params)

        if r.content:
            return r.json()

        return {}


class VsnapAPI(object):
    def __init__(self, vsnap_session, restype=None, endpoint=None):
        self.vsnap_session = vsnap_session
        self.restype = restype
        self.endpoint = endpoint
        self.list_field = resource_to_listfield.get(restype, self.restype + 's')

    def get(self, resid=None, path=None, params={}, url=None):
        return self.vsnap_session.get(restype=self.restype, resid=resid, path=path, params=params, url=url)

    def stream_get(self, resid=None, path=None, params={}, url=None, outfile=None):
        return self.vsnap_session.stream_get(restype=self.restype, resid=resid, path=path,
                                             params=params, url=url, outfile=outfile)

    def delete(self, resid, path=None):
        return self.vsnap_session.delete(restype=self.restype, resid=resid, path=path)

    def list(self):
        return self.vsnap_session.get(restype=self.restype)[self.list_field]

    def post(self, resid=None, path=None, data={}, params={}, url=None):
        return self.vsnap_session.post(restype=self.restype, resid=resid, path=path, data=data,
                                       params=params, url=url)

    def put(self, resid=None, path=None, data={}, params={}, url=None):
        return self.vsnap_session.put(restype=self.restype, resid=resid, path=path, data=data,
                                      params=params, url=url)



