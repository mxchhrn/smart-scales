import json
import requests
import time
import websocket
from teaid.teaidlib.common import functions_helper as fhelper


def send_login(in_app_id: str, in_email: str, in_passwd: str, in_base_url: str, in_app_secret: str, f_log: str):
    fhelper.write_message(f"Building package...", f_log)
    url = in_base_url + '/user/login'
    cur_payload = {
        'appid': in_app_id,
        'email': in_email,
        'password': in_passwd,
        'ts': int(time.time()),
        'version': 8,
        'nonce': fhelper.get_random(8)
    }

    cur_headers = {
        'Authorization': 'Sign ' + fhelper.get_hmac(json.dumps(cur_payload), in_app_secret),
        'Content-Type': 'application/json'
    }

    fhelper.write_message(f"Sending POST request: url: {url}, headers: {json.dumps(cur_headers)}, data: {json.dumps(cur_payload)}", f_log)
    r = requests.post(url, headers=cur_headers, data=json.dumps(cur_payload))
    fhelper.write_message(f"Received response payload: {r.text}", f_log)
    return r.text


def get_device_list(in_app_id: str, in_base_url: str, in_at: str, f_log: str) -> str:
    fhelper.write_message(f"Building package...", f_log)
    url = in_base_url + '/user/device'

    cur_payload = 'lang=en'
    cur_payload += '&appid=' + in_app_id
    cur_payload += '&nonce=' + fhelper.get_random(8)
    cur_payload += '&ts=' + str(int(time.time()))
    cur_payload += '&version=8'

    cur_headers = {
        'Authorization': 'Bearer ' + in_at,
        'Content-Type': 'application/json'
    }

    fhelper.write_message(f"Sending POST request: url: {url}, headers: {json.dumps(cur_headers)}, params: {cur_payload}", f_log)
    r = requests.get(url, headers=cur_headers, params=cur_payload)
    fhelper.write_message(f"Received response payload: {r.text}", f_log)
    return r.text


def get_device_info(in_app_id: str, in_base_url: str, in_at: str, in_api_key: str, in_dev_id: str, f_log) -> str:
    fhelper.write_message(f"Building package...", f_log)
    url = in_base_url + '/user/device/' + in_dev_id

    cur_headers = {
        'Authorization': 'Bearer ' + in_at,
        'Content-Type': 'application/json'
    }

    cur_payload = {'deviceid': in_dev_id, 'apikey': in_api_key, 'appid': in_app_id, 'nonce': fhelper.get_random(8), 'ts': str(int(time.time())), 'version': 8}

    fhelper.write_message(f"Sending POST request: url: {url}, headers: {json.dumps(cur_headers)}, data: {json.dumps(cur_payload)}", f_log)
    r = requests.get(url, headers=cur_headers, params=cur_payload)
    fhelper.write_message(f"Received response payload: {r.text}", f_log)
    return r.text


def get_device_history(in_base_url: str, in_at: str, in_dev_id: str, f_log: str) -> str:
    fhelper.write_message(f"Building package...", f_log)
    url = in_base_url + '/v2/device/history'

    cur_headers = {
        'Authorization': 'Bearer ' + in_at,
        'Content-Type': 'application/json'
    }

    cur_payload = {'deviceid': in_dev_id, 'from': str(int(time.time())), 'num': str(30)}

    fhelper.write_message(f"Sending POST request: url: {url}, headers: {json.dumps(cur_headers)}, data: {json.dumps(cur_payload)}", f_log)
    r = requests.get(url, headers=cur_headers, params=cur_payload)
    fhelper.write_message(f"Received response payload: {r.text}", f_log)
    return r.text


def connect_ws(in_web_host: str, in_at: str, in_api_key: str, in_app_id: str):
    url = 'wss://' + in_web_host + '/api/ws'

    cur_payload = {
        'action': 'userOnline',
        'at': in_at,
        'apikey': in_api_key,
        'appid': in_app_id,
        'nonce': fhelper.get_random(8),
        'ts': int(time.time()),
        'userAgent': 'app',
        'sequence': str(int(time.time() * 1000)),
        'version': 8
    }

    out_ws = websocket.create_connection(url)
    out_ws.send(json.dumps(cur_payload))
    resp = out_ws.recv()

    if json.loads(resp)['error'] == 0:
        return out_ws, True

    return out_ws, False


def turn_switch(in_ws: websocket, in_api_key, in_dev_id: str, in_bool: bool):
    if in_bool:
        new_state = 'on'
    else:
        new_state = 'off'

    cur_params = {'switches': [{'switch': new_state, 'outlet': 0}]}

    cur_payload = {
        'action': 'update',
        'apikey': in_api_key,
        'deviceid': in_dev_id,
        'params': cur_params,
        'userAgent': 'app',
        'sequence': str(int(time.time() * 1000))
    }
    in_ws.send(json.dumps(cur_payload))
    resp = in_ws.recv()
    return resp


def main(username: str, password: str, f_log: str):
    result = {}
    base_url = 'https://eu-api.coolkit.cc:8080/api'
    default_app_id = 'Uw83EKZFxdif7XFXEsrpduz5YyjP7nTl'
    default_app_secret = 'mXLOjea0woSMvK9gw7Fjsy7YlFO4iSu6'

    fhelper.write_message(f"Preparing login message for cloud API...", f_log)
    login_response = send_login(default_app_id, username, password, base_url, default_app_secret, f_log)
    try:
        cur_dict = json.loads(login_response)
        cur_at = cur_dict['at']
        cur_api_key = fhelper.find_key_value(cur_dict, 'apikey')
        fhelper.write_message(f"Received: access token & API key", f_log)
    except KeyError:
        cur_at = {}
        cur_api_key = {}
        fhelper.write_message(f"Login failed. Please check the credentials.", f_log)
        exit(1)

    result['token'] = cur_at

    fhelper.write_message(f"Requesting device list...", f_log)
    device_list = get_device_list(default_app_id, base_url, cur_at, f_log)
    result['devices'] = device_list
    fhelper.write_message(f"Received: device list.", f_log)

    # not working: 503 error
    # fhelper.write_message(f"Requesting device history for device {device_id}...", f_log)
    # history = get_device_history(base_url, cur_at, device_id, f_log)
    # result['history'] = history

    return result
