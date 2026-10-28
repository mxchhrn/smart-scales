import json
from tuya_connector import TuyaOpenAPI
from teaid.teaidlib.common import functions_helper as fhelper


def main(cloud_id: str, cloud_key: str, f_log: str) -> dict:
    # for the usage of the cloud api an account on iot.tuya.com or developer.tuya.com is necessary
    # easiest way to add devices is via Smart Life App
    # the id and key can be found in the project on iot.tuya.com
    # eu api endpoint
    api_endpoint = "https://openapi.tuyaeu.com"

    fhelper.write_message(f"Preparing login message for cloud API...", f_log)
    fhelper.write_message(f"Logging values: URL: {api_endpoint}, ID: {cloud_id}, key: {cloud_key}", f_log)
    openapi = TuyaOpenAPI(api_endpoint, cloud_id, cloud_key)
    response = openapi.connect()
    fhelper.write_message(f"Received response payload: {response}", f_log)
    auth_token = fhelper.find_key_value(response, 'access_token')
    fhelper.write_message(f"Received: authentication token.", f_log)

    fhelper.write_message(f"Requesting device list...", f_log)
    fhelper.write_message(f"URL: {api_endpoint + '/v1.0/iot-01/associated-users/devices'}", f_log)
    response = openapi.get('/v1.0/iot-01/associated-users/devices')
    fhelper.write_message(f"Received response payload: {json.dumps(response)}", f_log)
    device_list = fhelper.find_key_value(response, 'devices')
    fhelper.write_message(f"Received: device list.", f_log)

    cur_time = fhelper.get_time_13digit()

    # get the device logs
    # event type/id: 1 dev online, 2 dev offline, 3 dev activated, 4 dev reset, 5 instruction
    # event from: 1 device, 2 client command, 3 third party, 4 from cloud
    log_list = {}
    for dev in device_list:
        dev_id = fhelper.find_key_value(dev, 'id')
        fhelper.write_message(f"Requesting device logs for {dev_id}...", f_log)
        payload = {'type': '1,2,3,4,5', 'start_time': 0, 'end_time': cur_time}
        response = openapi.get(f"/v1.0/devices/{dev_id}/logs", params=payload)
        log_list[dev_id] = fhelper.find_key_value(response, 'logs')
        fhelper.write_message(f"Received response payload: {json.dumps(response)}", f_log)

    fhelper.write_message(f"Received: logs", f_log)

    return {'token': auth_token, 'devices': device_list, 'logs': log_list}
