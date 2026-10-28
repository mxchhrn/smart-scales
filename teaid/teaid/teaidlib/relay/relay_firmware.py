import base64
import json
import os
import pandas as pd
import re
from teaid.teaidlib.common import functions_os as fos
from teaid.teaidlib.common import functions_external as fext
from teaid.teaidlib.common import functions_helper as fhelper


# checks which firmware case it is and returns flag;
# flags: 0b0001 shelly (gen 1), 0b0010 shelly (gen 2), 0b0100 sonoff, 0b1000 beken
def check_firmware(raw_content: bytes) -> int:
    result = 0
    if fhelper.search_string_raw(raw_content, 'shelly'):
        if fhelper.search_string_raw(raw_content, 'shellyplus'):
            result |= 0b00000010
        else:
            result |= 0b00000001
    if fhelper.search_string_raw(raw_content, 'sonoff'):
        result |= 0b00000100
    if fhelper.search_string_raw(raw_content, 'beken'):
        result |= 0b00001000

    # check if exactly one flag is set, otherwise return -1
    if bin(result).count('1') == 1:
        return result
    return -1


# extract json files
def extract_json(raw_bytes: bytes, in_prefix: str, o_path: str, log_file: str):
    # start and end patterns for shelly gen 1
    sp = b'{\n  "'
    ep = b'\n}\xff\xff'

    json_files_pos = fhelper.search_patterns_raw(raw_bytes, sp, ep)
    if not json_files_pos:
        fhelper.write_message(f"Failed to find patterns in raw bytes.\n", log_file)
        exit(1)
    json_files = []

    # extract the json files
    for m in json_files_pos:
        tmp_bytes = raw_bytes[m[0]: m[1]]
        # search for not printable bad bytes (i.e. \x01, \x08)
        pattern = re.compile(b'[\x00-\x09\x0b-\x1F\x7C\x7E-\xFF]+')
        bad_bytes = [(b.start(), b.end()) for b in pattern.finditer(tmp_bytes)]
        json_bytes = b''
        if bad_bytes:
            last_index = 0
            for x in bad_bytes:
                json_bytes += tmp_bytes[last_index:x[0]]
                last_index = x[1]
        else:
            json_bytes = tmp_bytes

        if json_bytes not in json_files:
            json_files.append(json_bytes)

    # loop over json file list
    for i, j in enumerate(json_files):
        f_path = os.path.join(o_path, in_prefix + '_' + "{:0>2}".format(i) + '.json')
        with open(f_path, 'wb') as f:
            f.write(j)


# generates the output prefix from file name
# searches for the first two digit strings and combines them
# i.e. 02_flash_dump_00.bin -> 02-00
def get_output_prefix(in_path: str) -> str:
    digit_list = re.findall(r'\d+', os.path.basename(in_path))
    if not digit_list or len(digit_list) < 2:
        print(f"Failed to determine prefix.\nThere are to few digit strings in the file name.\nThere must be at least two digit strings.")
        return ''

    return digit_list[0] + '-' + digit_list[1]


# get partition table as dict from custom csv
# the csv file must contain a header row with start, length
# the values for the partitions must be in hex or int
def get_part_table(csv_path: str, log_file: str) -> dict:
    result = {}
    df = pd.read_csv(csv_path)
    # read start values and save them in dict
    for i, v in enumerate(df['start']):
        # try converting from int string
        try:
            result[i] = [int(v)]
        except ValueError:
            # try converting from hex string
            try:
                result[i] = [int(v, 16)]
            except ValueError:
                fhelper.write_message(f"Failed to read partition start {v} in row {i} as int or hex.", log_file)
                exit(1)
    # read length values and append them in the dict entry
    for i, v in enumerate(df['length']):
        # try converting from int string
        try:
            result[i].append(int(v))
        except ValueError:
            # try converting from hex string
            try:
                result[i].append(int(v, 16))
            except ValueError:
                fhelper.write_message(f"Failed to read partition length {v} in row {i} as int or hex.", log_file)
                exit(1)

    return result


# get the partition bytes from the firmware image
def get_partitions_from_raw(img_bytes: bytes, part_table: dict) -> dict:
    result = {}
    for k, v in part_table.items():
        result[k] = img_bytes[v[0]:v[0] + v[1]]
    return result


# save the partitions as files
def save_partitions(img_bytes, part_table: dict, file_prefix: str, o_path: str) -> dict:
    result = {}
    part_dict = get_partitions_from_raw(img_bytes, part_table)
    for k, v in part_dict.items():
        f_name = file_prefix + '_p' + str(k) + '.bin'
        f_name = os.path.join(o_path, f_name)
        with open(f_name, 'wb') as f:
            f.write(v)
        result[k] = f_name
    return result


# check if directories files and strings exist, otherwise create them
def mkdir_file_extract(o_path: str) -> tuple[str, str, str]:
    dir_files = os.path.join(o_path, 'files')
    if not os.path.exists(dir_files):
        os.mkdir(dir_files)
    dir_str = os.path.join(o_path, 'strings')
    if not os.path.exists(dir_str):
        os.mkdir(dir_str)
    dir_json = os.path.join(o_path, 'json')
    if not os.path.exists(dir_json):
        os.mkdir(dir_json)
    return dir_files, dir_str, dir_json


# extract the files and strings from a partition
def file_extract_raw(raw_path: str, in_prefix: str, o_path: str, log_file: str):
    cur_dir_files, cur_dir_str, cur_dir_json = mkdir_file_extract(o_path)
    fhelper.write_message(f"Processing raw file with file name {os.path.basename(raw_path)}", log_file)
    # tmp_dir = os.path.join(cur_dir_files, in_prefix)
    # if not os.path.exists(tmp_dir):
    #     os.mkdir(tmp_dir)
    # bulk extract
    tmp_dir = os.path.join(cur_dir_files, in_prefix + '_bulk')
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
        if not fext.use_bulk_extractor(raw_path, tmp_dir):
            fhelper.write_message(f"Failed to run bulk_extractor on raw file.", log_file)
    # littlefs
    tmp_dir = os.path.join(os.path.dirname(tmp_dir), in_prefix + '_littlefs')
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
        if not fext.use_mklittlefs(raw_path, tmp_dir):
            fhelper.write_message(f"Failed to run mklittlefs on raw file.", log_file)
    # strings
    tmp_file = os.path.join(cur_dir_str, in_prefix + '_strings.txt')
    if not os.path.exists(tmp_file):
        if not fext.use_strings(raw_path, tmp_file):
            fhelper.write_message(f"Failed to run strings on raw file.", log_file)
    # json
    with open(raw_path, 'rb') as f:
        raw = f.read()
    extract_json(raw, in_prefix, cur_dir_json, log_file)


# extract the files and strings from all partition
# if no partition table file is given, try: get_part_table_shelly
def file_extract_partitions(img_bytes: bytes, file_prefix: str, o_path: str, part_table: str, log_file: str):
    # check if part_table is given
    if part_table:
        p_dict = get_part_table(part_table, log_file)
    # if none part_table is given, try to get part table of a shelly gen2 device
    else:
        p_dict, p_bytes, p_csv = fext.use_gen_esp32part(img_bytes)

        # create directory for partition table and save partition table as csv and raw
        cur_dir = os.path.join(o_path, 'part_table')
        if not os.path.exists(cur_dir):
            os.mkdir(cur_dir)
        cur_file = os.path.join(cur_dir, file_prefix + '_part_table')
        if not os.path.exists(cur_file + '.csv'):
            with open(cur_file + '.csv', 'w') as f:
                f.write(p_csv)
        if not os.path.exists(cur_file + '.bin'):
            with open(cur_file + '.bin', 'wb') as f:
                f.write(p_bytes)

    # create directory for partitions and save them
    cur_dir = os.path.join(o_path, 'parts')
    if not os.path.exists(cur_dir):
        os.mkdir(cur_dir)
    p_names = save_partitions(img_bytes, p_dict, file_prefix, cur_dir)

    # loop over partition files and call bulk_extractor and mklittlefs
    for k, v in p_names.items():
        fhelper.write_message(f"Processing partition {k} with file name {os.path.basename(v)}", log_file)
        file_extract_raw(v, file_prefix + '_p' + str(k), o_path, log_file)


# function to extract the traces bk7231
def extract_traces_bk7231(i_path: str, log_file: str) -> dict:
    traces = {'device': {}, 'wi-fi': {}, 'cloud': {}, 'locale': {}}
    f_path = ''
    kv_path = os.path.join(i_path, 'kv_pairs')

    # search for *storage.json (contains key value pairs) and store them in data
    for f in os.listdir(kv_path):
        if 'storage.json' in f:
            f_path = os.path.join(kv_path, f)
            with open(f_path, 'r') as file:
                data = json.load(file)
            fhelper.copy_to_output(kv_path, i_path, log_file, f)
            fhelper.write_message(f"Read file {f}...", log_file)
            fhelper.write_message(f"Extract forensic artifacts from {f} content...", log_file)
            break

    # store wi-fi traces
    if fhelper.find_key_value(data, 'gw_wsm'):
        if isinstance(data['gw_wsm']['ssid'], str):
            traces['wi-fi']['ssid'] = base64.b64decode(data['gw_wsm']['ssid']).decode()
        if isinstance(data['gw_wsm']['passwd'], str):
            traces['wi-fi']['password'] = base64.b64decode(data['gw_wsm']['passwd']).decode()
        traces['wi-fi']['ssid_encoded'] = data['gw_wsm']['ssid']
        traces['wi-fi']['password_encoded'] = data['gw_wsm']['passwd']

    # store last offline state traces
    traces['device']['last_state_offline'] = {}
    if fhelper.find_key_value(data, 'save_off_stat'):
        for i, r in enumerate(data['save_off_stat']['power']):
            if r:
                tmp_r = 'on'
            else:
                tmp_r = 'off'
            traces['device']['last_state_offline']['relay' + str(i)] = tmp_r

    return traces


# function to read the last json file for shelly
def extract_traces_json_shelly(i_path: str, j_path: str, j_list: list, log_file: str) -> dict:
    data = {}
    for j in j_list[::-1]:
        if os.path.isabs(j):
            f_path = j
        else:
            f_path = os.path.join(j_path, j)
        if not os.path.isfile(f_path):
            continue
        try:
            with open(f_path, 'r') as f:
                data = json.load(f)
            fhelper.copy_to_output(j_path, i_path, log_file, j)
            fhelper.write_message(f"Read file {j}...", log_file)
            fhelper.write_message(f"Extract forensic artifacts from {j} content...", log_file)
            break
        except json.decoder.JSONDecodeError:
            continue

    return data


# function to extract the traces shelly gen 1
def extract_traces_shelly1(i_path: str, log_file: str) -> dict:
    traces = {'device': {}, 'wi-fi': {}, 'cloud': {}, 'locale': {}}
    j_path = os.path.join(i_path, 'json')

    # search for the last json and store it in data
    j_list = os.listdir(j_path)
    j_list.sort()
    data = extract_traces_json_shelly(i_path, j_path, j_list, log_file)

    # store wi-fi traces
    try:
        traces['wi-fi'] = data['wifi']
    except KeyError:
        pass

    # store device data
    try:
        traces['device']['id'] = data['device']['id']
    except KeyError:
        pass
    try:
        traces['device']['mqtt'] = data['mqtt']['will_topic']
    except KeyError:
        pass
    try:
        traces['device']['first-boot'] = data['first_boot']
    except KeyError:
        pass

    # store http login
    try:
        traces['device']['http_password'] = data['login']['password']
    except KeyError:
        pass

    # store cloud data
    try:
        traces['cloud'] = data['cloud']
    except KeyError:
        pass

    # store locale information
    traces['locale'] = {}
    try:
        traces['locale']['timezone'] = data['timezone']
        traces['locale']['latitude'] = data['latitude']
        traces['locale']['longitude'] = data['longitude']
    except KeyError:
        pass

    return traces


# function to help to extract traces for a partition set (shelly gen 2)
def extract_traces_shelly2_partition_set(in_dict: dict) -> dict:
    result = {'device': {}, 'wi-fi': {}, 'cloud': {}, 'locale': {}}
    # store wi-fi traces
    try:
        result['wi-fi'] = in_dict['wifi']
    except KeyError:
        pass

    # store cloud data
    try:
        result['cloud'] = in_dict['shelly']['cloud']
    except KeyError:
        pass

    # store locale information
    try:
        result['locale']['timezone'] = in_dict['shelly']['tz']
        result['locale']['latitude'] = in_dict['device']['location']['lat']
        result['locale']['longitude'] = in_dict['device']['location']['lon']
    except KeyError:
        pass

    # store locale information
    try:
        result['config'] = in_dict['sw']
    except KeyError:
        pass

    return result


# function to extract the traces shelly gen 2
def extract_traces_shelly2(i_path: str, log_file: str) -> dict:
    traces = {'A': {}, 'B': {}}
    j_path = os.path.join(i_path, 'json')

    # search for the json files from the partitions p3 and p5 and store them in j_list
    json_list = [[], []]
    tmp_j_list = os.listdir(j_path)
    tmp_j_list.sort()
    for j in tmp_j_list:
        if 'p3' in j:
            json_list[0].append(os.path.join(j_path, j))
        elif 'p5' in j:
            json_list[1].append(os.path.join(j_path, j))

    # read data from last json files of the partitions
    data_p3 = extract_traces_json_shelly(i_path, j_path, json_list[0], log_file)
    data_p5 = extract_traces_json_shelly(i_path, j_path, json_list[1], log_file)

    # partition set A
    traces['A'] = extract_traces_shelly2_partition_set(data_p3)

    # partition set B
    traces['B'] = extract_traces_shelly2_partition_set(data_p5)

    # search conf3.json try first from p3 then from p5
    conf3_path = os.path.join(i_path, 'files')
    data = {'A': {}, 'B': {}}
    for c in os.listdir(conf3_path):
        if 'p3_littlefs' in c or 'p5_littlefs' in c:
            t_path = os.path.join(conf3_path, c)
            j = os.path.join(t_path, 'conf3.json')
            if os.path.exists(j):
                if 'p3_littlefs' in j:
                    with open(j, 'r') as f:
                        data['A'] = json.load(f)
                    fhelper.write_message(f"Read file {j}...", log_file)
                    fhelper.write_message(f"Extract forensic artifacts from {j} content...", log_file)

                elif 'p5_littlefs' in j:
                    with open(j, 'r') as f:
                        data['B'] = json.load(f)
                    fhelper.write_message(f"Read file {j}...", log_file)
                    fhelper.write_message(f"Extract forensic artifacts from {j} content...", log_file)

    # get device information from conf3.json
    for p in ['A', 'B']:
        try:
            traces[p]['device']['id'] = data[p]['device']['id']
        except KeyError:
            pass
        try:
            traces[p]['device']['mqtt'] = data[p]['mqtt']['will_topic']
        except KeyError:
            pass

    return traces


# runs main function multiple times for different firmware files
# needs the absolute directory of the firmware images
def multi_firmware(img_dir: str, in_prefix='', in_part_table=''):
    if not fos.check_path(img_dir):
        print(f"Given image path does not exist or isn't an absolute path.")
        exit(1)

    # get all files in the given directory and store their abs path in img_files
    img_files = []
    dir_content = os.listdir(img_dir)
    dir_content.sort()
    for c in dir_content:
        tmp_path = os.path.join(img_dir, c)
        if os.path.isfile(tmp_path):
            img_files.append(tmp_path)

    # for each firmware file call firmware function
    for i in img_files:
        firmware(i, in_prefix, in_part_table)


# run to extract partitions and files of one firmware dump
def firmware(img_path: str, in_prefix='', in_part_table=''):
    if not fos.check_path(img_path):
        print(f"Given image path does not exist or isn't an absolute path.")
        exit(1)

    dir_path = os.path.dirname(img_path)
    img_base = os.path.basename(img_path)

    if in_prefix:
        prefix = in_prefix
    else:
        prefix = get_output_prefix(img_path)

    out_path = os.path.join(dir_path, prefix)
    if not os.path.exists(out_path):
        os.mkdir(out_path)

    log_file = os.path.join(out_path, 'firmware.log')
    out_file = os.path.join(out_path, 'summary.json')

    fhelper.write_message(f"Processing {img_base}...", log_file)

    fhelper.write_message(f"Read raw bytes of {img_base}...", log_file)
    with open(img_path, 'rb') as f:
        img = f.read()
    fhelper.write_message(f"Reading of {img_base} successful", log_file)

    fhelper.write_message(f"Check for known firmware category...", log_file)
    firmware_id = check_firmware(img)

    # shelly gen 2
    if firmware_id == 2:
        fhelper.write_message(f"Firmware category: Shelly gen 2 found.", log_file)
        file_extract_partitions(img, prefix, out_path, in_part_table, log_file)
        # extract traces
        trace_dict = extract_traces_shelly2(out_path, log_file)
        fhelper.write_to_output(trace_dict, out_file, log_file)
    # beken
    elif firmware_id == 8:
        fhelper.write_message(f"Firmware category: Beken found.", log_file)
        if not fext.use_bk7231tools(img_path, out_path):
            fhelper.write_message(f"Use of bk7231tools to dissect and decrypt the partitions failed.\nTry generic approach on firmware dump.", log_file)
            if in_part_table:
                file_extract_partitions(img, prefix, out_path, in_part_table, log_file)
            else:
                file_extract_raw(img_path, prefix, out_path, log_file)
        else:
            # execute file extract for both decrypted partitions
            tmp_dir = os.path.join(out_path, 'decrypt_parts')
            for p in os.listdir(tmp_dir):
                p_path = os.path.join(tmp_dir, p)
                t_prefix = prefix
                if 'app' in p:
                    t_prefix += '_app'
                elif 'bootloader' in p:
                    t_prefix += '_bootloader'
                file_extract_raw(p_path, t_prefix, tmp_dir, log_file)
            # extract traces
            trace_dict = extract_traces_bk7231(out_path, log_file)
            fhelper.write_to_output(trace_dict, out_file, log_file)
    # sonoff
    elif firmware_id == 4:
        fhelper.write_message(f"Firmware category: Sonoff found.", log_file)
        if in_part_table:
            file_extract_partitions(img, prefix, out_path, in_part_table, log_file)
        else:
            file_extract_raw(img_path, prefix, out_path, log_file)
    # shelly gen 1
    elif firmware_id == 1:
        fhelper.write_message(f"Firmware category: Shelly gen 1 found.", log_file)
        if in_part_table:
            file_extract_partitions(img, prefix, out_path, in_part_table, log_file)
        else:
            file_extract_raw(img_path, prefix, out_path, log_file)
        # extract traces
        trace_dict = extract_traces_shelly1(out_path, log_file)
        fhelper.write_to_output(trace_dict, out_file, log_file)
    # cannot determine
    elif firmware_id == -1:
        fhelper.write_message(f"Multiple possible firmware categories found: Try generic approach.", log_file)
        if in_part_table:
            file_extract_partitions(img, prefix, out_path, in_part_table, log_file)
        else:
            file_extract_raw(img_path, prefix, out_path, log_file)
