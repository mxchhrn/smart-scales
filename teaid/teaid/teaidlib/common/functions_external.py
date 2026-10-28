import os
import re
import shutil
import sys
import importlib.util
import pathlib
from . import functions_os as fos

# TODO: maybe move this into "tools" folder for better structure
class ToolNotFoundError(Exception):
    """Raised when a required tool cannot be found in pip or ext/."""
    pass

def locate_tool(name: str, ext_subdir: str = "esp-idf") -> str:
    """
    Locate a related tool.
    
    - First checks if it's available as a pip module.
    - Then searches in ext/<ext_subdir>/ for the script.
    - Returns the absolute path to the script (or module name if pip-installed).
    - Raises ToolNotFoundError if not found.
    
    Parameters
    ----------
    name : str
        Tool identifier, e.g. "nvs_partition_gen", "gen_esp32part", "espcoredump".
    ext_subdir : str
        Which ext/ subfolder to search in. Defaults to "esp-idf-tools".
    """
    
    # 1. Try pip-installed module (import check)
    if importlib.util.find_spec(name) is not None:
        return name   # Can be run directly with `python -m <name>`
    
    # 2. Try if it's an installed CLI script (pip entrypoint)
    if shutil.which(name):
        return shutil.which(name)
    
    # 3. Search rekursiv in ext/ folder for .py script
    base = pathlib.Path(__file__).resolve().parents[3] / "ext" / ext_subdir
    # candidate = base / f"{name}.py"
    candidates = list(base.rglob(f"{name}.py"))
    if candidates:
        if candidates[0].exists():
            return str(candidates[0])
    
    # 4. Not found → raise error
    raise ToolNotFoundError(
        f"Tool '{name}' not found. "
        f"Tried pip module, system PATH, and ext/{ext_subdir}/."
    )


def check_tshark_version(min_version="4.0"):
    try:
        cmd = 'tshark -version'
        err, output = fos.call_subprocess(cmd.split())
        if err:
            return False
        first_line = output.splitlines()[0]
        version_str = first_line.split()[2]
        if version_str < min_version:
            print(f"Warning: tshark version {version_str} is to old (required: >= {min_version})")
    except FileNotFoundError:
        print("Error: 'tshark' not found.")
        sys.exit(1)


def check_bulk_extractor_version(min_version="2.0.0"):
    try:
        cmd = 'bulk_extractor --version'
        err, output = fos.call_subprocess(cmd.split())
        if err:
            return False
        first_line = output.splitlines()[0]
        version_str = first_line.split()[1]
        if version_str < min_version:
            print(f"Warning: bulk_extractor version {version_str} is to old (required: >= {min_version})")
    except FileNotFoundError:
        print("Error: 'bulk_extractor' not found.")
        sys.exit(1)


def check_mklittlefs_version(min_version="4.0.0"):
    try:
        cmd = 'mklittlefs --version'
        err, output = fos.call_subprocess(cmd.split())
        if err:
            return False
        first_line = output.splitlines()[0]
        version_str = first_line.split()[2]
        if version_str < min_version:
            print(f"Warning: mklittlefs version {version_str} is to old (required: >= {min_version})")
    except FileNotFoundError:
        print("Error: 'mklittlefs' not found.")
        sys.exit(1)


# run strings on given raw file and save the output
def use_strings(f_path: str, o_path) -> bool:
    cmd = 'strings -t d -n 5 ' + f_path
    err, output = fos.call_subprocess(cmd.split())
    if err:
        return False

    if output:
        with open(o_path, 'w') as f:
            f.write(output)

    return True


# run bulk_extractor on given raw file and save the outputs in an output path
def use_bulk_extractor(f_path: str, o_path) -> bool:
    check_bulk_extractor_version()
    cmd = 'bulk_extractor -o ' + o_path + ' ' + f_path
    err, output = fos.call_subprocess(cmd.split())
    if err:
        return False

    # clean up the output directory and delete all empty files
    fos.delete_empty_files(o_path)

    # check if there are output files left
    if len(os.listdir()) < 2:
        print(f"No files found with bulk_extractor for {os.path.basename(f_path)}.")

    return True


# for the fs littlefs extract the files
def use_mklittlefs(p_path: str, o_path: str):
    check_mklittlefs_version()
    cmd = 'mklittlefs -u ' + o_path + ' ' + p_path
    err, output = fos.call_subprocess(cmd.split())
    if err:
        return False
    return True


# call bk7231tools dissect_dump to get the decrypted app and bootloader partitions and the kv pairs
def use_bk7231tools(f_path: str, o_path: str) -> bool:
    cmd = 'bk7231tools dissect_dump -e --storage -O ' + o_path + ' ' + f_path
    err, output = fos.call_subprocess(cmd.split())
    if err:
        return False

    list_dir = os.listdir(o_path)

    d_paths = ['encrypt_parts', 'decrypt_parts', 'kv_pairs']

    for i, d in enumerate(d_paths):
        d = os.path.join(o_path, d)
        d_paths[i] = d
        if not os.path.exists(d):
            os.mkdir(d)

    # separate the files in the corresponding directories
    for f in list_dir:
        tmp_f = os.path.join(o_path, f)
        if 'decrypt' in f:
            shutil.move(tmp_f, d_paths[1])
        elif 'storage' in f or 'user_param' in f:
            shutil.move(tmp_f, d_paths[2])
        elif 'app' in f or 'bootloader' in f:
            shutil.move(tmp_f, d_paths[0])

    return True


# save the partition table as dict {ID: [start, length]}
def use_gen_esp32part(img_bytes: bytes) -> tuple[dict, bytes, str]:
    path = locate_tool('gen_esp32part')
    result = {}

    table_start = 4096 * 8
    table_len = 256 * 12
    t_file = 'tmp_file.bin'
    with open(t_file, 'wb') as f:
        f.write(img_bytes[table_start:table_start + table_len])
    cmd = path + ' ' + t_file
    err, output = fos.call_subprocess(cmd.split())
    if err:
        print(f"Converting the partition table was not possible.")
        exit(1)

    i = 0
    for o in output.split('\n'):
        if '#' not in o:
            tmp = o.split(',')
            # the start is given as hex str -> conv to int
            p_start = int(tmp[3], 16)
            # the length is given as str with unit (i.e. '16K') -> search for digits & conv to int
            p_length = int(re.match(r'\d+', tmp[4]).group()) * 1024
            result[i] = [p_start, p_length]
            i += 1

    return result, img_bytes[table_start:table_start + table_len], output

# run nvs_tools on given partition file and save the output
def use_nvs_tools(nvs_bin_path: str, o_path: str, mode: str='minimal', format: str='json') -> bool:
    path = locate_tool('nvs_tool')
    cmd = '{} -d {} -f {} {}'.format(path, mode, format, nvs_bin_path)
    err, output = fos.call_subprocess(cmd.split())
    if err:
        return False

    if output:
        os.makedirs(os.path.dirname(o_path), exist_ok=True)
        with open(o_path, 'w') as f:
            f.write(output)

    return True

# run esptool on given partition ota file to get infos of firmware and save the output
def use_esp_tools(ota_bin_path: str, o_path: str) -> bool:
    path = locate_tool('esptool')
    cmd = '{} -image-info {}'.format(path, ota_bin_path)
    err, output = fos.call_subprocess(cmd.split())
    if err:
        return False

    if output:
        os.makedirs(os.path.dirname(o_path), exist_ok=True)
        with open(o_path, 'w') as f:
            f.write(output)

    return True

# run espcoredump on given partition coredump file to get infos of firmware crashes and debug and save the output
def use_esp_core_dump(coredump_bin_path: str, o_path: str, com_mode: str='info_corefile', com_arg: str='--core') -> bool:
    path = locate_tool('espcoredump')
    cmd = '{} {} {}'.format(path, com_mode, com_arg, coredump_bin_path)
    err, output = fos.call_subprocess(cmd.split())
    if err:
        return False

    if output:
        os.makedirs(os.path.dirname(o_path), exist_ok=True)
        with open(o_path, 'w') as f:
            f.write(output)

    return True
