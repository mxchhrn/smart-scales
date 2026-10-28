import hashlib
import json
import requests
from teaid.teaidlib.common import functions_helper as fhelper


def cloud_auth(user: str, pwd: str, f_log: str) -> str:
    fhelper.write_message(f"Building package...", f_log)
    proto = 'https'
    host = 'api.shelly.cloud'
    endpoint = '/auth/login'
    url = proto + '://' + host + endpoint

    head = {'Content-Type': 'application/x-www-form-urlencoded'}

    hashed = hashlib.sha1(pwd.encode()).hexdigest()

    payload = {'email': user, 'password': hashed, 'var': 2}

    fhelper.write_message(f"Sending POST request: url: {url}, headers: {json.dumps(head)}, data: {json.dumps(payload)}", f_log)
    response = requests.post(url, headers=head, data=payload)
    fhelper.write_message(f"Received response payload: {response.text}", f_log)
    at = fhelper.find_key_value(json.loads(response.text), 'token')
    return at


def get_device_list(at: str, f_log: str) -> dict:
    fhelper.write_message(f"Building package...", f_log)
    proto = 'https'
    host = 'shelly-77-eu.shelly.cloud'
    endpoint = '/device/all_status?show_info=true&no_shared=true'
    url = proto + '://' + host + endpoint

    head = {'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': 'Bearer ' + at}

    fhelper.write_message(f"Sending POST request: url: {url}, headers: {json.dumps(head)}", f_log)
    response = requests.post(url, headers=head)
    fhelper.write_message(f"Received response payload: {response.text}", f_log)
    response_dict = json.loads(response.text)

    return response_dict['data']['devices_status']


def main(username: str, password: str, f_log: str) -> dict:
    fhelper.write_message(f"Preparing login message for cloud API...", f_log)
    auth_token = cloud_auth(username, password, f_log)
    fhelper.write_message(f"Received: auth token.", f_log)

    fhelper.write_message(f"Requesting device list...", f_log)
    device_dict = get_device_list(auth_token, f_log)
    fhelper.write_message(f"Received: device list.", f_log)

    result = {'token': auth_token, 'devices': device_dict}

    return result
