import ast
import json
import os
import re
import xml.etree.ElementTree as ET
from teaid.teaidlib.common import functions_db as fdb
from teaid.teaidlib.common import functions_helper as fhelper
from teaid.teaidlib.common import functions_os as fos
from teaid.teaidlib.common import definitions

# read a given LevelDB file, return its content and store the content in an output file
def export_app_webview_leveldb(app_path: str, out_path: str, log) -> dict:
    tmp = 'app_webview/Default/Local Storage/leveldb'
    fhelper.write_message(f"Read LevelDB in {tmp}...", log)
    tmp_path = os.path.join(app_path, tmp)
    leveldb_content = fdb.get_leveldb_kv_pairs(tmp_path)

    tmp = 'app_webview_leveldb.json'
    fhelper.write_message(f"Export LevelDB content in {tmp}...", log)
    tmp_path = os.path.join(out_path, tmp)
    with open(tmp_path, 'w') as f:
        json.dump(leveldb_content, f)

    return leveldb_content


# read a given XML file, return its root node and copy the file to the output dir
def export_shared_prefs(app_path: str, out_path: str, log: str, xml_file: str) -> ET.Element:
    out_file = fhelper.copy_to_output(app_path, out_path, log, xml_file)
    tmp_file = os.path.basename(out_file)
    fhelper.write_message(f"Read file {tmp_file}...", log)
    fhelper.write_message(f"Extract forensic artifacts from {tmp_file} content...", log)
    tree = ET.parse(out_file)
    root = tree.getroot()
    return root


# read a given sqlite DB file, return its content and copy the file to the output dir
def export_sqlite_db(app_path: str, out_path: str, log: str, db_file: str) -> dict:
    out_file = fhelper.copy_to_output(app_path, out_path, log, db_file)
    tmp_file = os.path.basename(out_file)
    fhelper.write_message(f"Read file {tmp_file}...", log)
    fhelper.write_message(f"Extract forensic artifacts from {tmp_file} content...", log)
    result = fdb.get_sqlite_db_data(out_file)
    return result

# read a given sqlite DB file, return its content and copy the file to the output dir
def export_sqlite_db_as_dict(app_path: str, out_path: str, log: str, db_file: str, database_key: str = None) -> dict:
    out_file = fhelper.copy_to_output(app_path, out_path, log, db_file)
    tmp_file = os.path.basename(out_file)
    fhelper.write_message(f"Read file {tmp_file}...", log)
    fhelper.write_message(f"Extract forensic artifacts from {tmp_file} content...", log)
    result = fdb.get_sqlite_db_as_dict(out_file, database_key)
    return result


# list dir content, empty list if the dir is missing
def list_dir_safe(path: str) -> list:
    return os.listdir(path) if os.path.isdir(path) else []


# function to get the forensic artifacts of feelfit
def get_from_feelfit(app_path: str, out_path: str, log: str) -> dict:
    traces = {'devices': {}, 'user': {}, 'wi-fi': {}, 'cloud': {}, 'locale': {}}
    # always empty
    # db_local_storage = export_app_webview_leveldb(app_path, out_path, log)
    
    INVALID_VALUES = {None, 0, 1, -1, 0.0, '', '0'}

    tmp = 'databases/oversea.db'
    sql_content = export_sqlite_db_as_dict(app_path, out_path, log, tmp, "db_encrypt_key")

    if sql_content:
        traces.setdefault('user', {})
        traces['user']['database'] = {}

        sql_keys = [
            'BIND_DEVICE',
            'DEVICE_INFO',
            'MEASURE_DATA',
            'SCALE_USER',
            'STORAGE',
            'USER_TABLE'
        ]

        for sql_key in sql_keys:
            rows = sql_content.get(sql_key, [])
            traces['user']['database'][sql_key] = []

            for row in rows:
                row.pop('_id', None)  # delete

                filtered_dict = {
                    k: v for k, v in row.items()
                    if v not in INVALID_VALUES
                }

                traces['user']['database'][sql_key].append(filtered_dict)

    
    # write out datasheets
    tmp = 'cache/AndServer'
    for f in list_dir_safe(os.path.join(app_path, tmp)):
        if f.endswith(".xlsx"):
            fhelper.copy_to_output(app_path, out_path, log, os.path.join(tmp, f))
    
    # get infos from json
    tmp = 'cache/instrument'
    json_files = [os.path.abspath(os.path.join(app_path, tmp, f)) for f in list_dir_safe(os.path.join(app_path, tmp)) if f.endswith(".json")]
    if json_files:
        latest = max(json_files, key=os.path.getmtime)
        fhelper.write_message(f"Extract forensic artifacts from {latest} content...", log)
        with open(latest) as json_file:
            tmp_dict = json.load(json_file)
        traces['devices']['smartphone'] = fhelper.find_key_value(tmp_dict, 'device_model')
        traces['devices']['smartphone_os_version'] = fhelper.find_key_value(tmp_dict, 'device_os_version')
        traces['devices']['app_version'] = fhelper.find_key_value(tmp_dict, 'app_version')
          
    # extract from king_new_foreign.db
    tmp = 'databases/king_new_foreign.db'
    sql_content = export_sqlite_db(app_path, out_path, log, tmp)
    traces['locale']['lang'] = sql_content['android_metadata'][0][0]
    
    tmp = 'files/logger/FitBit'
    for file in list_dir_safe(os.path.join(app_path, tmp)):
        if file.endswith(".txt"):
            tmp_list = fhelper.parse_from_log_txt(os.path.abspath(os.path.join(app_path, tmp, file)))
            for event in tmp_list:
                if "FitBit refreshUserWithValidity" in event["raw_message"]:
                    fhelper.write_message(f"Extract forensic artifacts from {tmp} content...", log)
                    line = event["raw_message"]
                    fields_str = line.split("--", 1)[1]
                    # split fields
                    fields = [f.strip() for f in fields_str.split(",")]
                    for f in fields:
                        if ":" in f:
                            key, value = f.split(":", 1)
                            key = key.strip()
                            value = value.strip()
                            if value:
                                traces['FitBit'][key] = value
    INVALID_VALUES = [0, 0.0]
    MEASUREMENT_JSON_MAPPING = {
        "baby_weight": ("baby_weight"),
        "birthday": ("birthday"),
        "bmi": ("bmi"),
        "bmr": ("bmr"),
        "bodyage": ("body_age"),
        "bodyfat": ("body_fat"),
        "body_shape": ("body_shape"),
        "bone": ("bone"),
        "fat_free_weight": ("fat_free_weight"),
        "gender": ("gender"),
        "height": ("height"),
        "muscle": ("muscle"),
        "pregnant_flag": ("baby_pregnant_flagweight"),
        "protein": ("protein"),
        "resistance": ("resistance"),
        "score": ("score"),
        "subfat": ("subfat"),
        "visfat": ("visfat"),
        "water": ("water"),
        "weight": ("weight")
    }
    tmp = 'files/logger/h5'
    for file in list_dir_safe(os.path.join(app_path, tmp)):
        if file.endswith(".txt"):
            fhelper.write_message(f"Extract forensic artifacts from {os.path.abspath(os.path.join(app_path, tmp, file))} content...", log)
            tmp_list = fhelper.parse_from_log_txt(os.path.abspath(os.path.join(app_path, tmp, file)))
            for event in tmp_list:
                if event["raw_message"] is not None:
                # ip address
                    if "http://" in event["raw_message"]:
                        valid_ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', event["raw_message"])
                        if valid_ip:
                            traces['devices']['scale_server_ip'] = valid_ip[0]
                    # port number
                    if "端口" in event["raw_message"]:
                        traces['devices']['scale_server_port'] = event["raw_message"].split()[2]
                if event["json"] is not None:
                    if "brand_name" in event["json"]:
                        traces['devices']['scale_brand'] = fhelper.find_key_value(event["json"], 'brand_name')
                    if "measure_mode" in event["json"]:
                        traces['devices']['scale_measure_mode'] = fhelper.find_key_value(event["json"], 'measure_mode')
                    if "model" in event["json"]:
                        traces['devices']['scale_model'] = fhelper.find_key_value(event["json"], 'model')
                    if "scale_name" in event["json"]:
                        traces['devices']['scale_name'] = fhelper.find_key_value(event["json"], 'scale_name')
                    if "internal_model" in event["json"]:
                        traces['devices']['scale_internal_name'] = fhelper.find_key_value(event["json"], 'internal_model')
                    if "mac" in event["json"]:
                        traces['devices']['scale_mac'] = fhelper.find_key_value(event["json"], 'mac')
                    # get wi-fi
                    if "wifiName" in event["json"]:
                        traces['wi-fi']['ssid'] = fhelper.find_key_value(event["json"], 'wifiName')
                    if "wifiPassword" in event["json"]:
                        traces['wi-fi']['password'] = fhelper.find_key_value(event["json"], 'wifiPassword')
                    if "serverUrl" in event["json"]:
                        traces['wi-fi']['serverUrl'] = fhelper.find_key_value(event["json"], 'serverUrl')
                    if "fotaUrl" in event["json"]:
                        traces['wi-fi']['fotaUrl'] = fhelper.find_key_value(event["json"], 'fotaUrl')
                    if "encryptionKey" in event["json"]:
                        traces['wi-fi']['encryptionKey'] = fhelper.find_key_value(event["json"], 'encryptionKey')
                    # get weights infos
                    for key, (target) in MEASUREMENT_JSON_MAPPING.items():
                        if key in event["json"]:
                            value = fhelper.find_key_value(event["json"], key)
                            if value not in INVALID_VALUES:
                                if target not in traces['user']:
                                    traces['user'][target] = []
                                traces['user'][target].append({
                                    event["timestamp"]: value
                                })
    tmp = 'files/logger/h5Console'
    for file in list_dir_safe(os.path.join(app_path, tmp)):
        if file.endswith(".txt"):
            fhelper.write_message(f"Extract forensic artifacts from {os.path.abspath(os.path.join(app_path, tmp, file))} content...", log)
            tmp_list = fhelper.parse_from_log_txt(os.path.abspath(os.path.join(app_path, tmp, file)))
            for event in tmp_list:
                if event["json"] is not None:
                    if not traces['devices'].get('smartphone') and "cellphoneType" in event["json"]:
                        traces['devices']['smartphone'] = fhelper.find_key_value(event["json"], 'cellphoneType')
                    if not traces['devices'].get('scale_server_port') and "local_server_port" in event["json"]:
                        traces['devices']['scale_server_port'] = fhelper.find_key_value(event["json"], 'scale_server_port')
                    if not traces['devices'].get('app_version') and "appVer" in event["json"]:
                        traces['devices']['app_version'] = fhelper.find_key_value(event["json"], 'appVer')
                    if "appName" in event["json"]:
                        traces['devices']['app_name'] = fhelper.find_key_value(event["json"], 'appName')
                    if "server_domain" in event["json"]:
                        traces['cloud']['server_domain'] = fhelper.find_key_value(event["json"], 'server_domain')
                    if "method" in event["json"]: # TODO: maybe sort out doubles?
                        if "server_api" not in traces['devices']:
                            traces['devices']['server_api'] = []
                        if fhelper.find_key_value(event["json"], 'method') in definitions.VALID_HTTP_METHODS:
                            traces['devices']['server_api'].append({
                                'method': fhelper.find_key_value(event["json"], 'method'),
                                'path': fhelper.find_key_value(event["json"], 'path')
                            })
                    # maybe sort out duplicates in the following
                    USER_JSON_MAPPING = {
                        "account_name": ("account_name"),
                        "email": ("email"),
                        "user_id": ("user_id"),
                    }
                    MEASUREMENT_JSON_MAPPING.update(USER_JSON_MAPPING)
                    for key, (target) in MEASUREMENT_JSON_MAPPING.items():
                        if key in event["json"]:
                            value = fhelper.find_key_value(event["json"], key)
                            if value not in INVALID_VALUES:
                                if target not in traces['user']:
                                    traces['user'][target] = []
                                traces['user'][target].append({
                                    event["timestamp"]: value
                                })
    tmp = 'files/logger/http'
    # cloud url + + user + token
    http_method = None
    request_url = None
    token = None
    username = None
    traces['cloud']['cloud_api'] = []
    for file in list_dir_safe(os.path.join(app_path, tmp)):
        if file.endswith(".txt"):
            fhelper.write_message(f"Extract forensic artifacts from {os.path.abspath(os.path.join(app_path, tmp, file))} content...", log)
            tmp_list = fhelper.parse_from_log_txt(os.path.abspath(os.path.join(app_path, tmp, file)))
            for event in tmp_list:
                if event["timestamp"] is not None:
                    dict_template = {
                        'method': http_method,
                        'request_url': request_url,
                        'token': token,
                        'username': username
                    }

                    # filter none values
                    filtered_dict = {k: v for k, v in dict_template.items() if v is not None}

                    if filtered_dict:
                        traces['cloud']['cloud_api'].append(filtered_dict)
                    http_method = None
                    request_url = None
                    token = None
                    username = None
                if "Response-Body:"in event["raw_message"]:
                    continue
                if event["raw_message"] is not None:
                    if event["raw_message"] in definitions.VALID_HTTP_METHODS:
                        http_method = event["raw_message"]
                        continue
                    if "Request-URL:" in event["raw_message"]:
                        request_url = event["raw_message"].split(":", 1)[1]
                        continue
                    if "Request-Header:" in event["raw_message"]:
                        token_match = re.search(r"(?:x-token:\s*bearer|Authorization:\s*Bearer)\s+([^,}]+)", event["raw_message"], re.IGNORECASE)
                        token = token_match.group(1) if token_match else None
                        username_match = re.search(r'username="([^"]+)"', event["raw_message"])
                        username = username_match.group(1) if username_match else None
                        continue
                if event["json"] is not None:
                    if "token" in event["json"]:
                        token = fhelper.find_key_value(event["json"], 'token')
            # save last entry of log file
            dict_template = {
                'method': http_method,
                'request_url': request_url,
                'token': token,
                'username': username
            }
            filtered_dict = {k: v for k, v in dict_template.items() if v is not None}

            if filtered_dict:
                traces['cloud']['cloud_api'].append(filtered_dict)
                
                
    # copy logger files to output
    # tmp = 'files/logger/localServer'
    tmp = 'files/logger'
    for d in list_dir_safe(os.path.join(app_path, tmp)):
        for f in list_dir_safe(os.path.join(app_path, tmp, d)):
            fhelper.copy_to_output(app_path, os.path.join(out_path, d), log, os.path.join(tmp, d, f))
    
    return traces


# function to get the forensic artifacts of eufy
def get_from_eufy(app_path: str, out_path: str, log: str) -> dict:
    traces = {'devices': {}, 'user': {}, 'wi-fi': {}, 'cloud': {}, 'locale': {}}
    INVALID_VALUES = [None, 0, 1, 0.0, '', '0']
    # always empty
    # db_local_storage = export_app_webview_leveldb(app_path, out_path, log)

    # extract from *_preferences.xml
    tmp = 'shared_prefs/FlutterSharedPreferences.xml'
    root_node = export_shared_prefs(app_path, out_path, log, tmp)
    for node in root_node:
        if node.tag == 'string' and node.attrib['name'] == 'flutter.keyIoTUserInfo':
            traces['cloud']['user_token'] = fhelper.find_key_value(fhelper.safe_json_parse(node.text), 'token')
            traces['cloud']['user_uid'] = fhelper.find_key_value(fhelper.safe_json_parse(node.text), 'uid')
            traces['cloud']['user_openUdid'] = fhelper.find_key_value(fhelper.safe_json_parse(node.text), 'openUdid')
        elif node.tag == 'string' and node.attrib['name'] == 'flutter.hostUrlmp':
            traces['cloud']['iot_url'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'flutter.mqttCertificates':
            traces['devices']['app_name'] = fhelper.find_key_value(fhelper.safe_json_parse(node.text)[0], 'app_name')
            traces['devices']['thing_name'] = fhelper.find_key_value(fhelper.safe_json_parse(node.text)[0], 'thing_name')
            traces['cloud']['certificate_id'] = fhelper.find_key_value(fhelper.safe_json_parse(node.text)[0], 'certificate_id')
            str_certificate_pem = fhelper.find_key_value(fhelper.safe_json_parse(node.text)[0], 'certificate_pem')
            fhelper.write_string_to_file(str_certificate_pem, os.path.join(out_path, 'mqttCertificates', 'certificate_pem.pem'), log)
            traces['cloud']['certificate_pem'] = str_certificate_pem
            str_private_key = fhelper.find_key_value(fhelper.safe_json_parse(node.text)[0], 'private_key')
            fhelper.write_string_to_file(str_private_key, os.path.join(out_path, 'mqttCertificates', 'private_key.key'), log)
            traces['cloud']['private_key'] = str_private_key
            str_public_key = fhelper.find_key_value(fhelper.safe_json_parse(node.text)[0], 'public_key')
            if str_public_key:
                fhelper.write_string_to_file(str_public_key, os.path.join(out_path, 'mqttCertificates', 'public_key.key'), log)
                traces['cloud']['public_key'] = str_public_key
            traces['cloud']['endpoint_addr'] = fhelper.find_key_value(fhelper.safe_json_parse(node.text)[0], 'endpoint_addr')
            str_aws_root_ca1_pem = fhelper.find_key_value(fhelper.safe_json_parse(node.text)[0], 'aws_root_ca1_pem')
            fhelper.write_string_to_file(str_certificate_pem, os.path.join(out_path, 'mqttCertificates', 'aws_root_ca1_pem.pem'), log)
            traces['cloud']['aws_root_ca1_pem'] = str_aws_root_ca1_pem
           
    tmp = 'shared_prefs/share_data.xml'
    root_node = export_shared_prefs(app_path, out_path, log, tmp)
    tmp_mac = None
    for node in root_node:
        if node.tag == 'string' and node.attrib['name'] == 'heightUnit':
            traces['devices']['heightUnit'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'KEY_EXPLOREREDDOT_MESSAGE':
            traces['cloud']['mall_link'] = fhelper.find_key_value(fhelper.safe_json_parse(node.text), 'mall_link')
        elif node.tag == 'string' and node.attrib['name'] == 'access_token':
            traces['cloud']['mall_link_access_token'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'refresh_token':
            traces['cloud']['mall_link_refresh_token'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'user_id':
            traces['user']['user_id'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'nick_name':
            traces['user']['nick_name'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'currentConnectMac':
            tmp_mac = node.text
            traces['devices']['currentConnectMac'] = tmp_mac
        elif node.tag == 'string' and node.attrib['name'] == 'account_phone_number':
            account_phone_number = node.text
            if account_phone_number:
                traces['user']['account_phone_number'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'push_token':
            traces['user']['push_token'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'email':
            traces['user']['email'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'token_json':
            traces['user']['token_json'] = node.text
        if tmp_mac:
            if node.tag == 'string' and node.attrib['name'] == 'wifi_mac_address_{}'.format(tmp_mac.lower()):
                traces['devices']['wifi_mac_address_'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'request_host':
            traces['cloud']['request_host'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'androidVersion':
            traces['devices']['app_version'] = node.text
            
    # extract from EufyLifeDb.db
    tmp = 'databases/EufyLifeDb.db'
    sql_content = export_sqlite_db_as_dict(app_path, out_path, log, tmp)
    if sql_content:
        traces['user']['measurements'] = []
    traces['locale']['lang'] = fhelper.find_key_value(sql_content['android_metadata'][0], 'locale')
    for row in sql_content['bodyfathistorym']:
        del row['id'] 
        filtered_dict = {k: v for k, v in row.items() if v not in INVALID_VALUES}
        # maybe covert time stamps with datetime.datetime.fromtimestamp
        traces['user']['measurements'].append(filtered_dict)
    for row in sql_content['memberinfom']: #TODO: add user infos over each row not override them
        del row['id'] 
        for key, value in row.items():
            if value not in INVALID_VALUES:
                traces['user'][key] = value
    for row in sql_content['devicelistm']:
        del row['id'] 
        for key, value in row.items():
            if value not in INVALID_VALUES:
                if 'wifissid' in key:
                    traces['wi-fi'][key] = value
                traces['devices'][key] = value
    
    return traces


# function to get the forensic artifacts of Withings
def get_from_withings(app_path: str, out_path: str, log: str) -> dict:
    traces = {'devices': {}, 'user': {}, 'wi-fi': {}, 'cloud': {}, 'locale': {}}
    
    # always empty
    # db_local_storage = export_app_webview_leveldb(app_path, out_path, log)

    tmp = 'databases/rl_persistence.db'
    sql_content = export_sqlite_db_as_dict(app_path, out_path, log, tmp)
    if sql_content:
        for row in sql_content['events']:
            app = fhelper.find_key_value(fhelper.safe_json_parse(row['message']), 'app')
            for key , value in app.items():
                traces['devices']['app_{}'.format(key)] = value
            device = fhelper.find_key_value(fhelper.safe_json_parse(row['message']), 'device')
            for key , value in device.items():
                traces['devices']['device_{}'.format(key)] = value
            library = fhelper.find_key_value(fhelper.safe_json_parse(row['message']), 'library')
            for key , value in library.items():
                traces['devices']['library_{}'.format(key)] = value
            network = fhelper.find_key_value(fhelper.safe_json_parse(row['message']), 'network')
            for key , value in network.items():
                traces['devices']['network_{}'.format(key)] = value
            phone_os = fhelper.find_key_value(fhelper.safe_json_parse(row['message']), 'os')
            for key , value in phone_os.items():
                traces['devices']['smartphone_os_{}'.format(key)] = value
            traits = fhelper.find_key_value(fhelper.safe_json_parse(row['message']), 'traits')
            for key , value in traits.items():
                traces['user']['traits_{}'.format(key)] = value
            traces['locale']['timezone'] = fhelper.find_key_value(fhelper.safe_json_parse(row['message']), 'timezone')
            traces['devices']['userAgent'] = fhelper.find_key_value(fhelper.safe_json_parse(row['message']), 'userAgent')
            
            
            
    tmp = 'databases/room-healthmate.db'
    sql_content = export_sqlite_db_as_dict(app_path, out_path, log, tmp)
    if sql_content:
        for row in sql_content['HealthmateSessionData']:
            for key, value in row.items():
                traces['cloud'][key] = value
    
    INVALID_VALUES = {None, 0, 1, -1, 0.0, '', '0'}
    # extract from Withings-WiScale SQLite
    tmp = 'databases/Withings-WiScale'
    sql_content = export_sqlite_db_as_dict(app_path, out_path, log, tmp)
    traces['locale']['lang'] = fhelper.find_key_value(sql_content['android_metadata'][0], 'locale')
    if sql_content:
        traces.setdefault('user', {})
        traces['user']['database'] = {}

        sql_keys = [
            'probe',
            'measure',
            'users',
            'devices'
        ]

        for sql_key in sql_keys:
            rows = sql_content.get(sql_key, [])
            traces['user']['database'][sql_key] = []

            for row in rows:

                filtered_dict = {
                    k: v for k, v in row.items()
                    if v not in INVALID_VALUES
                }

                traces['user']['database'][sql_key].append(filtered_dict)
    # TODO: sort data better
 
    tmp = 'shared_prefs/account.xml'
    root_node = export_shared_prefs(app_path, out_path, log, tmp)
    for node in root_node:
        if node.tag == 'string' and node.attrib['name'] == 'encrypted_email':
            traces['user']['account_encrypted_email'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'encrypted_authProviderToken':
            traces['user']['account_encrypted_authProviderToken'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'accountType':
            traces['user']['account_accountType'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'uuid':
            traces['user']['account_uuid'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'virtualDeviceToken':
            traces['user']['account_virtualDeviceToken'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'authProviderName':
            traces['user']['account_authProviderName'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'encrypted_authToken':
            traces['user']['account_encrypted_authToken'] = node.text
            
    tmp = 'shared_prefs/com.google.android.gms.signin.xml'
    root_node = export_shared_prefs(app_path, out_path, log, tmp)
    for node in root_node:
        if node.tag == 'string' and 'googleSignInAccount' in node.attrib['name']:
            traces['user']['email'] = fhelper.find_key_value(fhelper.safe_json_parse(node.text), 'email')
            traces['user']['name'] = fhelper.find_key_value(fhelper.safe_json_parse(node.text), 'displayName')
    
    if not any('traits' in key for key in traces['user'].keys()):
        tmp = 'shared_prefs/rl_prefs.xml'
        root_node = export_shared_prefs(app_path, out_path, log, tmp)
        for node in root_node:
            if node.tag == 'string' and node.attrib['name'] == 'rl_traits':
                traits = fhelper.safe_json_parse(node.text)
                for key , value in traits.items():
                    traces['user']['traits_{}'.format(key)] = value

    tmp = 'shared_prefs/user.xml'
    root_node = export_shared_prefs(app_path, out_path, log, tmp)
    for node in root_node:
        if node.tag == 'long' and node.attrib['name'] == 'mainUserId':
            traces['user']['mainUserId'] = node.attrib['value']

    return traces

def main(app_path: str, out_path: str, app_id=''):
    supported_apps = ['com.qingniu.feelfit', 'com.oceanwing.smarthome', 'com.withings.wiscale2']

    if not fos.check_path(app_path):
        print(f"Given application path does not exist or isn't an absolute path.\nAborting...")
        exit(1)
    elif not fos.check_path(out_path):
        print(f"Given output path does not exist or isn't an absolute path.\nAborting...")
        exit(1)

    log_basename = 'companion_app.log'
    json_basename = 'companion_app_summary.json'
    
    if app_id:  
        name, ext = os.path.splitext(log_basename)
        log_basename = f"{app_id}_{name}{ext}"
        name, ext = os.path.splitext(json_basename)
        json_basename = f"{app_id}_{name}{ext}"
    
    log_file = os.path.join(out_path, log_basename)
    out_file = os.path.join(out_path, json_basename)

    fhelper.write_message(f"Check if application ID is given...", log_file)
    if not app_id or app_id not in supported_apps:
        fhelper.write_message(f"Try getting application ID from path...", log_file)
        if os.path.basename(app_path) in supported_apps:
            app_id = os.path.basename(app_path)
            fhelper.write_message(f"Application ID from path: {app_id}", log_file)
        else:
            fhelper.write_message(f"Invalid application ID or if none given invalid application path.\nThe app path must be a directory named as the application ID, if no app ID is given.\nPlease check again.\nAborting...", log_file)
            exit(1)
    else:
        fhelper.write_message(f"Application ID given: {app_id}", log_file)

    trace_dict = {}

    fhelper.write_message(f"Processing application data...", log_file)
    if 'qingniu' in app_id:
        fhelper.write_message(f"Extracting data of Feelfit app...", log_file)
        trace_dict = get_from_feelfit(app_path, out_path, log_file)
    elif 'oceanwing' in app_id:
        fhelper.write_message(f"Extracting data of Eufy Life app...", log_file)
        trace_dict = get_from_eufy(app_path, out_path, log_file)
    elif 'withings' in app_id:
        fhelper.write_message(f"Extracting data of Withings app...", log_file)
        trace_dict = get_from_withings(app_path, out_path, log_file)

    fhelper.write_to_output(trace_dict, out_file, log_file)
