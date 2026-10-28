import base64
import json
import os
import pandas as pd
import re
import shutil
from teaid.teaidlib.common import functions_os as fos
from teaid.teaidlib.common import functions_external as fext
from teaid.teaidlib.common import functions_helper as fhelper


# checks which firmware case it is and returns flag;
def check_firmware(raw_content: bytes) -> int:
    result = 0
    # ESP-Typ-Erkennung
    if fhelper.search_string_raw(raw_content, 'ESP32'):
        if fhelper.search_string_raw(raw_content, 'ESP8266'):
            result |= 0b00000001
            print("Chip: ESP8266")
        else:
            result |= 0b00000001
            print("Chip: ESP32")
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
        return False
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
    return True

# convert csv to df
def get_part_table_as_df(csv_path: str, log_file: str) -> pd.DataFrame:
    df = pd.read_csv(
        csv_path,
        comment="#",
        names=["Name", "Type", "SubType", "Offset", "Size", "Flags"]
    )
    fhelper.write_message(f"Convert {csv_path} to DataFrame.", log_file)
    return df

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
    if not extract_json(raw, in_prefix, cur_dir_json, log_file):
        fhelper.write_message(f"Failed to extract json data on raw file.", log_file)


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

def extract_traces_otadata():
    pass

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
        part_table = cur_file + '.csv'
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

    if part_table:
        list_of_partition_names = get_part_table_as_df(part_table, log_file)["Name"].tolist()
    
    # loop over partition files and call bulk_extractor and mklittlefs
    for k, v in p_names.items():
        fhelper.write_message(f"Processing partition {k} with file name {os.path.basename(v)}", log_file)
        if list_of_partition_names[k] == 'nvs':
            cur_dir = os.path.join(o_path, 'nvs')
            tmp_file = os.path.join(cur_dir, str(k) + '_nvs.json')
            if not os.path.exists(tmp_file):
                if not fext.use_nvs_tools(v, tmp_file):
                    # maybe parse from .h files to parse meaningful
                    # trace_dict = extract_traces_nvs(tmp_file, log_file)
                    fhelper.write_message(f"Use of nvs_tools to get nvs key/values of the partitions failed.", log_file)
        elif list_of_partition_names[k] == 'otadata':
            # which part is active
            cur_dir = os.path.join(o_path, 'otadata')
            tmp_file = os.path.join(cur_dir, str(k) + '_otadata.txt')
            if not os.path.exists(tmp_file):
                    #trace_dict = extract_traces_otadata(tmp_file, log_file)
                    #fhelper.write_to_output(trace_dict, out_file, log_file)
                    pass
        elif 'ota' in list_of_partition_names[k]:
            pass
            # esptool.py image_info ota_0.bin #xtensa-esp32-elf-objdump (Disassembler)
            cur_dir = os.path.join(o_path, 'ota')
            tmp_file = os.path.join(cur_dir, str(k) + '_ota.txt')
            if not os.path.exists(tmp_file):
                if not fext.use_esp_tools(v, tmp_file):
                    # maybe parse from .h files to parse meaningful
                    # trace_dict = extract_traces_ota(tmp_file, log_file)
                    fhelper.write_message(f"Use of esptools to get ota image infos of the partitions failed.", log_file)
            
        elif list_of_partition_names[k] == 'coredump':
            pass
            # needs valid elf bin for analysis
            # espcoredump.py info_corefile --core coredump.bin --elf firmware.elf
            # cur_dir = os.path.join(o_path, 'coredump')
            # tmp_file = os.path.join(cur_dir, str(k) + '_coredump.txt')
            # if not os.path.exists(tmp_file):
            #     if not fext.use_esp_core_dump(v, tmp_file):
            #         # maybe parse from .h files to parse meaningful
            #         # trace_dict = extract_traces_ota(tmp_file, log_file)
            #         fhelper.write_message(f"Use of espcoredump to get coredump image infos of the partitions failed.", log_file)
        else:
            file_extract_raw(v, file_prefix + '_p' + str(k), o_path, log_file)

# run to extract partitions and files of one firmware dump
def firmware(img_path: str, in_prefix='', in_part_table=''):
    if not fos.check_path(img_path):
        print(f"Given image path does not exist or isn't an absolute path.")
        exit(1)

    dir_path = os.path.dirname(img_path)
    img_base = os.path.basename(img_path)

    log_basename = 'firmware.log'
    json_basename = 'firmware_summary.json'

    if in_prefix:
        prefix = in_prefix
        name, ext = os.path.splitext(log_basename)
        log_basename = f"{prefix}_{name}{ext}"
        name, ext = os.path.splitext(json_basename)
        json_basename = f"{prefix}_{name}{ext}"
    else:
        prefix = "generic"#get_output_prefix(img_path)

    out_path = os.path.join(dir_path, prefix)
    if not os.path.exists(out_path):
        os.mkdir(out_path)

    log_file = os.path.join(out_path, log_basename)
    out_file = os.path.join(out_path, json_basename)

    fhelper.write_message(f"Processing {img_base}...", log_file)

    fhelper.write_message(f"Read raw bytes of {img_base}...", log_file)
    with open(img_path, 'rb') as f:
        img = f.read()
    fhelper.write_message(f"Reading of {img_base} successful", log_file)

    fhelper.write_message(f"Check for known firmware category...", log_file)
    firmware_id = check_firmware(img)

    # ESP-based
    if firmware_id == 1:
        fhelper.write_message(f"Firmware category: ESP based.", log_file)
        file_extract_partitions(img, prefix, out_path, in_part_table, log_file)
        # at the moment out summary json
        shutil.copy(os.path.join(out_path, "nvs/0_nvs.json"),out_file)
        
    # cannot determine
    elif firmware_id == -1:
        fhelper.write_message(f"Multiple possible firmware categories found: Try generic approach.", log_file)
        if in_part_table:
            file_extract_partitions(img, prefix, out_path, in_part_table, log_file)
        else:
            file_extract_raw(img_path, prefix, out_path, log_file)