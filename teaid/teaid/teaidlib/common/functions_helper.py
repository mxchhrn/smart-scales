import base64
import datetime
import hashlib
import hmac
import json
import os
import random
import re
import shutil
import socket
import string
import struct
import time
from typing import List, Dict, Optional

# from cryptography import x509
# from cryptography.hazmat.primitives import serialization
# from cryptography.hazmat.backends import default_backend
# # checker for certifcates and keys?
# def check_certificate(pem_path: str):
#     try:
#         with open(pem_path, "rb") as f:
#             pem_data = f.read()

#         cert = x509.load_pem_x509_certificate(pem_data, backend=default_backend())
        
#         # Zertifikat ist gültig, jetzt kannst du Details auslesen
#         print("Zertifikat erfolgreich geladen!")
#         print("Subject:", cert.subject)
#         print("Issuer:", cert.issuer)
#         print("Gültig von:", cert.not_valid_before)
#         print("Gültig bis:", cert.not_valid_after)
#         return True
#     except ValueError as e:
#         print("FEHLER: Kein gültiges PEM-Zertifikat:", e)
#         return False
#     except FileNotFoundError:
#         print("FEHLER: PEM-Datei nicht gefunden")
#         return False
#     return False

# def check_private_key(key_path:str):
#     try:
#         with open(key_path, "rb") as f:
#             key_data = f.read()

#         private_key = serialization.load_pem_private_key(
#             key_data,
#             password=None,  # falls der Key verschlüsselt ist, hier das Passwort angeben
#             backend=default_backend()
#         )

#         print("Private Key erfolgreich geladen!")
#         print("Key Type:", type(private_key))

#     except ValueError as e:
#         print("FEHLER: Kein gültiger PEM-Key oder falsches Passwort:", e)
#     except FileNotFoundError:
#         print("FEHLER: PEM-Datei nicht gefunden")
        
# def check_public_key(key_path:str):
#     try:
#         with open(key_path, "rb") as f:
#             pub_key_data = f.read()

#         public_key = serialization.load_pem_public_key(
#             pub_key_data,
#             backend=default_backend()
#         )

#         print("Public Key erfolgreich geladen!")
#         print("Key Type:", type(public_key))

#     except ValueError as e:
#         print("FEHLER: Kein gültiger Public PEM-Key:", e)
#     except FileNotFoundError:
#         print("FEHLER: PEM-Datei nicht gefunden")

def safe_json_parse(s: str) -> dict:
    """
    Try to parse String as JSON.
    If Java/Android-Dump-Format {key='value', key2='value2'},
    then convert to JSON.
    Else return None
    """
    # 1. Try JSON
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # 2. Try Java-like Objekt and convert
    if s.startswith("{") and s.endswith("}"):
        try:
            # Keys in Anführungszeichen setzen
            tmp = re.sub(r"(\w+)=('.*?'|[^,}]+)", lambda m: f'"{m.group(1)}": {m.group(2)}', s)
            # Single Quotes → Double Quotes
            tmp = tmp.replace("'", '"')
            return json.loads(tmp)
        except Exception:
            return None

    return None

# takes a given file and try to parse 
def parse_from_log_txt(file: str, line_pattern: Optional[re.Pattern] = None) -> List[Dict]:
    """
    Parse log file lines into structured events.

    Args:
        file: path to log file
        line_pattern: Optional, use another regex pattern instead of default regex

    Returns:
        list of dicts: timestamp, raw_message, JSON
    """
    if line_pattern is None:
        # Default: [time] : msg  OR  LOG => msg
        line_pattern = re.compile(
            r'^(?:\[(?P<timestamp>.*?)\]\s*:\s*(?P<msg1>.*)|LOG\s*=>\s*(?P<msg2>.*))$'
        )

    events = []

    with open(file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            m = line_pattern.match(line)
            if m:
                timestamp = m.groupdict().get("timestamp")
                message = m.groupdict().get("msg1") or m.groupdict().get("msg2")
            else:
                # Fallback: no pattern -> only message
                timestamp = None
                message = line
            # Try to parse possible json data
            if message:
                json_obj = None
                json_match = re.search(r'(\{.*\})', message)
                if json_match:
                    json_obj = safe_json_parse(json_match.group(1))

            events.append({
                "timestamp": timestamp,
                "raw_message": message,
                "json": json_obj
            })
    return events

# takes given file content and checks if the search string is in the raw input
def search_string_raw(content: bytes, search_str: str) -> bool:
    pattern = search_str.encode()
    if re.findall(pattern, content):
        return True
    return False


# search for patterns in raw input
def search_patterns_raw(raw_bytes: bytes, s_pattern: bytes, e_pattern: bytes) -> list:
    # search for start patterns and save them in matches_start
    start_positions = [m.start() for m in re.finditer(re.escape(s_pattern), raw_bytes)]
    result = []

    # search in raw bytes starting from start matches
    for start in start_positions:
        end_match = re.search(re.escape(e_pattern), raw_bytes[start:])
        if end_match:
            if result:
                if end_match.end() == result[-1][1] - start:
                    continue
            result.append((start, start + end_match.end()))

    return result


# find a key in a dict, or it's sub dicts and outputs the value
def find_key_value(nested_dict, target_key):
    if target_key in nested_dict.keys():
        return nested_dict[target_key]
    for key, value in nested_dict.items():
        if isinstance(value, dict):
            result = find_key_value(value, target_key)
            if result is not None:
                return result
    return None


# return the corresponding hmac
def get_hmac(data: str, key: str) -> str:
    result = hmac.new(key.encode(), data.encode(), digestmod=hashlib.sha256)
    return base64.b64encode(result.digest()).decode()


# outputs the current time as 13 digit timestamp
def get_time_13digit() -> int:
    cur_time = datetime.datetime.now()
    return int(time.mktime(cur_time.timetuple()) * 1000 + cur_time.microsecond/1000)


# get a random string with [a-z0-9] as characters and the given length
def get_random(length: int) -> str:
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for c in range(length))


# prints message on stdout and saves message in log file
def write_message(in_msg: str, log_file: str):
    cur_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(in_msg)
    with open(log_file, 'a') as f:
        f.write(f"{cur_time}: {in_msg}\n")


# remove all non-printable characters from the input string
def remove_non_printable(in_str: str) -> str:
    return re.sub(r'[\x00-\x1F\x7F]', '', in_str)


# convert an int ip address to the string version
def convert_ip(in_int: int) -> str:
    return socket.inet_ntoa(struct.pack('>i', in_int))


# copy a given file (relative path in app directory) to the output directory
def copy_to_output(app_path: str, out_path: str, log: str, f_name: str) -> str:
    tmp_file = os.path.basename(f_name)
    tmp_path = os.path.join(app_path, f_name)
    write_message(f"Copy file {tmp_file} to {out_path}", log)
    out_file = os.path.join(out_path, tmp_file)
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    shutil.copy(tmp_path, out_file)
    return out_file


# write the dictionary to the output file
def write_to_output(in_dict: dict, j_file: str, log_file: str):
    write_message(f"Finished analysis.", log_file)
    write_message(f"Write extracted data to output file...", log_file)
    with open(j_file, 'w') as f:
        json.dump(in_dict, f, indent=2)
    write_message(f"Writing to output file finished.", log_file)

# write string to file
def write_string_to_file(raw_string: string, file_path: str, log_file: str):
    write_message(f"Write raw string to output file...", log_file)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(raw_string)
    write_message(f"Writing to output file: {file_path} finished.", log_file)