import ast
import json
import os
import xml.etree.ElementTree as ET
from teaid.teaidlib.common import functions_db as fdb
from teaid.teaidlib.common import functions_helper as fhelper
from teaid.teaidlib.common import functions_os as fos


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


# function to get the forensic artifacts of shelly
def get_from_shelly(app_path: str, out_path: str, log: str) -> dict:
    traces = {'devices': {}, 'cloud': {}, 'locale': {}}
    db_local_storage = export_app_webview_leveldb(app_path, out_path, log)

    fhelper.write_message(f"Extract forensic artifacts from LevelDB content...", log)
    traces['devices']['list'] = json.loads(db_local_storage['_file://devices'])
    traces['devices']['auth'] = json.loads(db_local_storage['_file://device_auths'])
    tmp_dict = json.loads(db_local_storage['_file://user_data'])
    traces['cloud']['api_url'] = fhelper.find_key_value(tmp_dict, 'user_api_url')
    traces['cloud']['token'] = fhelper.find_key_value(tmp_dict, 'token')
    traces['cloud']['email'] = fhelper.find_key_value(tmp_dict, 'email')
    traces['cloud']['password'] = fhelper.find_key_value(tmp_dict, 'password')
    traces['cloud']['user_id'] = fhelper.find_key_value(tmp_dict, 'user_id')
    traces['locale']['lang'] = fhelper.find_key_value(tmp_dict, 'lang')
    traces['locale']['timezone'] = fhelper.find_key_value(tmp_dict, 'timezone')

    # extract from *_preferences.xml
    tmp = 'shared_prefs/cloud.shelly.smartcontrol_preferences.xml'
    root_node = export_shared_prefs(app_path, out_path, log, tmp)
    for node in root_node:
        if node.tag == 'int':
            traces['devices'][node.attrib['name']] = node.attrib['value']

    return traces


# function to get the forensic artifacts of meross
def get_from_meross(app_path: str, out_path: str, log: str) -> dict:
    traces = {'devices': {}, 'cloud': {}, 'locale': {}}
    export_app_webview_leveldb(app_path, out_path, log)

    # extract from localCache.xml
    tmp = 'shared_prefs/localCache.xml'
    root_node = export_shared_prefs(app_path, out_path, log, tmp)
    for node in root_node:
        if node.tag == 'string' and node.attrib['name'] == 'list':
            traces['devices']['list'] = node.text.replace("\"", "'")

    # extract from *_preferences.xml
    tmp = 'shared_prefs/com.meross.meross_preferences.xml'
    root_node = export_shared_prefs(app_path, out_path, log, tmp)
    for node in root_node:
        if node.tag == 'string' and node.attrib['name'] == 'userid':
            traces['cloud']['user_id'] = int(node.text)
        elif node.tag == 'string' and node.attrib['name'] == 'domain':
            traces['cloud']['api_url'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'meross_locale':
            pass
        elif node.tag == 'string' and node.attrib['name'] == 'email':
            traces['cloud']['email'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'key':
            traces['cloud']['key'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'token':
            traces['cloud']['token'] = node.text
        elif node.tag == 'string' and node.attrib['name'] == 'region':
            traces['locale']['region'] = node.text

    # extract from Meross.db
    tmp = 'databases/Meross.db'
    sql_content = export_sqlite_db(app_path, out_path, log, tmp)
    traces['locale']['lang'] = sql_content['android_metadata'][0][0]

    return traces


# function to get the forensic artifacts of eWeLink
def get_from_ewelink(app_path: str, out_path: str, log: str) -> dict:
    traces = {'devices': {}, 'wi-fi': {}, 'cloud': {}, 'locale': {}}

    # extract from Meross.db
    tmp = 'databases/RKStorage'
    sql_content = export_sqlite_db(app_path, out_path, log, tmp)
    traces['locale']['lang'] = sql_content['android_metadata'][0][0]
    for row in sql_content['catalystLocalStorage']:
        if row[0] == 'LOCALE_STORAGE_KEY':
            row_dict = ast.literal_eval(row[1])
            traces['locale']['region'] = row_dict['region']
        elif row[0] == 'WIFI_INFO':
            row_dict = ast.literal_eval(row[1])
            traces['wi-fi']['ssid'] = fhelper.find_key_value(row_dict, 'ssid')
            traces['wi-fi']['password'] = fhelper.find_key_value(row_dict, 'password')
            traces['wi-fi']['bssid'] = fhelper.find_key_value(row_dict, 'bssid')
        elif row[0] == 'user_map':
            row_dict = json.loads(row[1])
            if len(row[1].keys()) > 1:
                for i, u in enumerate(row_dict.keys()):
                    traces['cloud']['user_' + str(i)] = row_dict[u]
            else:
                traces['cloud']['at'] = fhelper.find_key_value(row_dict, 'at')
                traces['cloud']['rt'] = fhelper.find_key_value(row_dict, 'rt')
                traces['cloud']['email'] = fhelper.find_key_value(row_dict, 'email')
                traces['cloud']['phone'] = fhelper.find_key_value(row_dict, 'phoneNumber')
                traces['cloud']['api_key'] = fhelper.find_key_value(row_dict, 'apikey')
                traces['cloud']['login_time'] = fhelper.find_key_value(row_dict, 'loginTime')
                traces['locale']['timezone'] = fhelper.find_key_value(row_dict, 'timezone')['id']
        elif row[0] == 'WIDGET_REQUEST_URL':
            traces['cloud']['api_url'] = row[1].replace("\"", "'")
        elif row[0] == 'device_data_list':
            traces['devices']['list'] = row[1].replace("\"", "'")

    # copy log files to output
    tmp = 'files/log'
    for f in os.listdir(os.path.join(app_path, tmp)):
        fhelper.copy_to_output(app_path, out_path, log, os.path.join(tmp, f))

    return traces


def main(app_path: str, out_path: str, app_id=''):
    supported_apps = ['com.coolkit', 'com.meross.meross', 'cloud.shelly.smartcontrol']

    if not fos.check_path(app_path):
        print(f"Given application path does not exist or isn't an absolute path.\nAborting...")
        exit(1)
    elif not fos.check_path(out_path):
        print(f"Given output path does not exist or isn't an absolute path.\nAborting...")
        exit(1)

    log_file = os.path.join(out_path, 'companion_app.log')
    out_file = os.path.join(out_path, 'summary.json')

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
    if 'coolkit' in app_id:
        fhelper.write_message(f"Extracting data of eWeLink app...", log_file)
        trace_dict = get_from_ewelink(app_path, out_path, log_file)
    elif 'meross' in app_id:
        fhelper.write_message(f"Extracting data of meross app...", log_file)
        trace_dict = get_from_meross(app_path, out_path, log_file)
    elif 'shelly' in app_id:
        fhelper.write_message(f"Extracting data of Shelly app...", log_file)
        trace_dict = get_from_shelly(app_path, out_path, log_file)

    fhelper.write_to_output(trace_dict, out_file, log_file)
