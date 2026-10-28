import json

import dpkt.ethernet
import pyshark
import os
from teaid.teaidlib.common import functions_os, functions_helper, functions_external


def use_tshark(in_pcap: str, out_pcap: str, ssl_key_log_file: str):
    os.environ['SSLKEYLOGFILE'] = ssl_key_log_file
    functions_external.check_tshark_version()
    cmd = 'tshark -r ' + in_pcap + ' -o tls.keylog_file:$SSLKEYLOGFILE -Y tls -w ' + out_pcap
    err, output = functions_os.call_subprocess(cmd.split())
    if err:
        return False

    return True


def read_http_layer(layer) -> dict:
    headers = ''
    body = ''
    r = {'type': '', 'msg': '', 'uri': '', 'headers': '', 'body': ''}
    field_dict = layer._all_fields
    r['msg'] = functions_helper.find_key_value(field_dict, '_ws.expert.message').replace('\\r\\n', '')
    if hasattr(layer, 'response'):
        r['type'] = 'response'
        r['uri'] = functions_helper.find_key_value(field_dict, 'http.response_for.uri')
        for i in field_dict['http.response.line']:
            headers += i.replace('\r\n', ';')
    elif hasattr(layer, 'request'):
        r['type'] = 'request'
        r['uri'] = functions_helper.find_key_value(field_dict, 'http.request.full_uri')
        for i in field_dict['http.request.line']:
            headers += i.replace('\r\n', ';')
    r['headers'] = headers
    content_length = functions_helper.find_key_value(field_dict, 'http.content_length')
    if content_length is not None:
        if not functions_helper.find_key_value(field_dict, 'http.content_length') == '0':
            body_tmp = functions_helper.find_key_value(field_dict, 'http.file_data_raw')
            body = bytes.fromhex(body_tmp[0]).decode('ascii', errors='ignore')
    r['body'] = body

    return r


def read_websocket_layer(layer) -> dict:
    r = {'payload': ''}
    field_dict = layer._all_fields
    r['payload'] = json.loads(functions_helper.find_key_value(field_dict, 'websocket.payload.text'))

    return r


def read_tcp_layer(tcp_payload: list) -> dict:
    r = {'payload': ''}
    # extract first element of the tcp.payload_raw list
    tmp_payload = tcp_payload[0]
    # convert bytes string to bytes and decode to ascii string
    tmp_payload = bytes.fromhex(tmp_payload).decode('ascii', errors='ignore')
    if tmp_payload[2:].replace('"', "'"):
        r['payload'] = tmp_payload[2:].replace('"', "'")
    else:
        r = {}

    return r


def read_pcap(in_pcap: str, ip_filter: str, log_file: str) -> dict:
    functions_helper.write_message(f"Open pcap file {os.path.basename(in_pcap)}...", log_file)
    cap = pyshark.FileCapture(in_pcap, include_raw=True, use_json=True)
    package_dict = {}

    for i, packet in enumerate(cap):
        try:
            functions_helper.write_message(f"Process package {i}...", log_file)
            tmp_package = {}
            tcp = None
            eth = dpkt.ethernet.Ethernet(packet.get_raw_packet())
            if isinstance(eth.data, dpkt.ip.IP):
                ip = eth.data
                if isinstance(ip.data, dpkt.tcp.TCP):
                    tcp = ip.data
                print("No TCP.")
            else:
                print("No IP.")
                if 'TLS' in packet:
                    if hasattr(packet.tls, 'record'):
                        if hasattr(packet.tls.record, 'content_type'):
                            content_type = int(packet.tls.record.content_type)
                            if content_type == 23:
                                print(f"[{i}] Encrypted Application Data (TLS) detected")
            src_ip = packet.ip.src
            dst_ip = packet.ip.dst
            # if i == 22 or i == 7:
            #     for layer in packet.layers:
            #         print(layer.layer_name)
            #     print(packet.tcp.payload_raw)
            #     print(packet.tcp._all_fields)
            # elif i < 22:
            #     pass
            # else:
            #     exit(1)
            # only collect packages with src ip or dst ip equals ip filter, if ip filter is set
            if (ip_filter and (src_ip == ip_filter or dst_ip == ip_filter)) or not ip_filter:
                if isinstance(tcp, dpkt.tcp.TCP):
                    functions_helper.write_message(f"Process TCP content of package {i}...", log_file)
                    tmp_package['time'] = float(packet.sniff_timestamp)
                    tmp_package['src_ip'] = src_ip
                    tmp_package['dst_ip'] = dst_ip
                    # parse http packages
                    if hasattr(packet, 'HTTP'):
                        functions_helper.write_message(f"Read HTTP information of package {i}...", log_file)
                        tmp_package['type'] = 'HTTP'
                        tmp_package['http'] = read_http_layer(packet.http)
                        package_dict[i] = tmp_package
                    # parse websocket packages
                    elif hasattr(packet, 'websocket'):
                        functions_helper.write_message(f"Read WebSocket information of package {i}...", log_file)
                        tmp_package['type'] = 'WebSocket'
                        tmp_package['websocket'] = read_websocket_layer(packet.websocket)
                        package_dict[i] = tmp_package
                    # parse tcp payload if length of payload is bigger than 10
                    elif hasattr(packet.tcp, 'tcp.payload_raw'):
                        functions_helper.write_message(f"Read TCP payload information of package {i}...", log_file)
                        functions_helper.write_message(f"Decode TCP payload information of package {i}...", log_file)
                        tmp_package['type'] = 'TCP'
                        tmp_package['payload'] = read_tcp_layer(packet.tcp.payload_raw)
                        if tmp_package['payload']:
                            package_dict[i] = tmp_package
                        else:
                            functions_helper.write_message(f"No readable TCP payload found. Skip package {i}.", log_file)
        except Exception as e:
            functions_helper.write_message(f"[WARN] Fehler bei Paket {i}: {e}", log_file)
            continue

    cap.close()

    return package_dict


def main(key_file: str, in_pcap_file: str, out_path: str, ip_filter=''):
    if not functions_os.check_path(in_pcap_file) or not functions_os.check_path(out_path):
        print(f"Given pcap file path or output path does not exist or isn't an absolute path. Aborting...")
        exit(1)

    log_file = os.path.join(out_path, 'network.log')
    out_file = os.path.join(out_path, 'summary.json')

    functions_helper.write_message(f"Check if SSL key file is given...", log_file)
    if key_file:
        functions_helper.write_message(f"SSL key file given. Try decrypting...", log_file)
        input_file_split = os.path.splitext(os.path.basename(in_pcap_file))[0]
        pcap_file = os.path.join(out_path, input_file_split + '_decrypt.pcap')
        use_tshark(in_pcap_file, pcap_file, key_file)
        functions_helper.write_message(f"Decrypted pcap file stored as {input_file_split}_decrypt.pcap.", log_file)
    else:
        functions_helper.write_message(f"No SSL key file given. Try without decrypting...", log_file)
        pcap_file = in_pcap_file

    trace_dict = read_pcap(pcap_file, ip_filter, log_file)

    functions_helper.write_to_output(trace_dict, out_file, log_file)
