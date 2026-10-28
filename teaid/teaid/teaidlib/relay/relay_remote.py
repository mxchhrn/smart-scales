import json
import os.path
from teaid.teaidlib.cloud import cloud_ewelink as ewelink
from teaid.teaidlib.cloud import cloud_meross as meross
from teaid.teaidlib.cloud import cloud_shelly as shelly
from teaid.teaidlib.cloud import cloud_tuya as tuya
from teaid.teaidlib.common import functions_os as fos
from teaid.teaidlib.common import functions_helper as fhelper


def main(out_path: str, vendor_str: str, mail: str, pw: str):
    if not fos.check_path(out_path):
        print(f"Given output path is invalid.")
        exit(1)
    log_file = os.path.join(out_path, 'remote.log')
    out_file = os.path.join(out_path, 'summary.json')

    # clear log file if exists
    if os.path.exists(log_file):
        with open(log_file, 'w') as _:
            pass

    fhelper.write_message(f"Processing given cloud vendor...", log_file)

    r = {}
    if vendor_str == 'ewelink':
        fhelper.write_message(f"Cloud vendor eWeLink received.\nPreparing API call...", log_file)
        r = ewelink.main(mail, pw, log_file)
    elif vendor_str == 'meross':
        fhelper.write_message(f"Cloud vendor meross received.\nPreparing API call...", log_file)
        r = meross.main(mail, pw, log_file)
        if not r['devices']:
            fhelper.write_message(f"Received empty device list.\nFor meross cloud there will be only devices listed which are currently online.", log_file)
    elif vendor_str == 'shelly':
        fhelper.write_message(f"Cloud vendor Shelly received.\nPreparing API call...", log_file)
        r = shelly.main(mail, pw, log_file)
    elif vendor_str == 'tuya':
        fhelper.write_message(f"Cloud vendor Tuya received.\nPreparing API call...", log_file)
        r = tuya.main(mail, pw, log_file)
    else:
        fhelper.write_message(f"Given cloud vendor {vendor_str} not implemented.\nAborting...", log_file)
        exit(1)

    if not r:
        fhelper.write_message(f"Cloud API call failed. Please check the log file.\nAborting...", log_file)
        exit(1)
    else:
        fhelper.write_message(f"Cloud API call finished.\nResponse: {json.dumps(r)}\nWriting response to output file...", log_file)

    fhelper.write_to_output(r, out_file, log_file)
