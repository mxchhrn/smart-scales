#!/bin/python3

import sys
import os

if __name__ == "__main__":
    # to run it also direct without package installation
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import datetime
import time
from teaid.teaidlib.relay import relay_network, relay_remote, relay_companion_app, relay_firmware
from teaid.teaidlib.scale import scale_companion_app, scale_firmware


def firmware(in_args) -> bool:

    # check prefix and table argument
    if in_args.p is None:
        f_prefix = ''
    else:
        f_prefix = in_args.p
    if in_args.t is None:
        p_table = ''
    else:
        p_table = in_args.t

    # run for one firmware file
    if in_args.f is not None:
        match in_args.type:
            case "relay":
                relay_firmware.firmware(in_args.f, f_prefix, p_table)
            case "scale":
                scale_firmware.firmware(in_args.f, f_prefix, p_table)
    # run for directory with firmware files
    if in_args.d is not None:
        match in_args.type:
            case "relay":
                relay_firmware.multi_firmware(in_args.d, f_prefix, p_table)
            case "scale":
                scale_firmware.multi_firmware(in_args.f, f_prefix, p_table)
    return True


def companion_app(in_args) -> bool:
    if in_args.i is None:
        match in_args.type:
            case "relay":
                relay_companion_app.main(in_args.a, in_args.o)
            case "scale":
                scale_companion_app.main(in_args.a, in_args.o)
    else:
        match in_args.type:
            case "relay":
                relay_companion_app.main(in_args.a, in_args.o, in_args.i)
            case "scale":
                scale_companion_app.main(in_args.a, in_args.o, in_args.i)
    return True


def remote(in_args) -> bool:
    match in_args.type:
            case "relay":
               relay_remote.main(in_args.o, in_args.v, in_args.c[0], in_args.c[1])
            case "scale":
                print("To be implemented!")
    return True


def network(in_args) -> bool:
    if in_args.ip is None:
        match in_args.type:
            case "relay":
                relay_network.main(in_args.k, in_args.f, in_args.o)
            case "scale":
                # no difference between relay and scale
                relay_network.main(in_args.k, in_args.f, in_args.o)
    else:
        match in_args.type:
            case "relay":
                relay_network.main(in_args.k, in_args.f, in_args.o, in_args.ip)
            case "scale":
                # no difference between relay and scale
                relay_network.main(in_args.k, in_args.f, in_args.o, in_args.ip)
    return True

def main():
    # ascii art
    ascii_title = ('  _______________    ________ \n'
                   + ' /_  __/ ____/   |  /  _/ __ \\\n'
                   + '  / / / __/ / /| |  / // / / /\n'
                   + ' / / / /___/ ___ |_/ // /_/ / \n'
                   + '/_/ /_____/_/  |_/___/_____/  \n')
    print(ascii_title)
    print('Tool for Evidence Acquisition from IoT Devices (TEAID)\n')
    
    # define the options and init the argument parser
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--type', type=str, required=True, choices=['relay', 'scale'], help='set IoT type (required)')
    
    subparsers = parser.add_subparsers(dest='sub_command', required=True)

    # define firmware subparser
    firmware_str = 'Function to analyze a given firmware image.\nOne of the arguments "--file" or "--path" must be set.'
    firmware_parser = subparsers.add_parser('firmware', help=firmware_str, description=firmware_str)

    firmware_parser.add_argument('-p', type=str, help='prefix for output files (optional)', metavar='prefix')
    firmware_parser.add_argument('-t', type=str, help='absolute path of an optional partition table in csv format (optional)', metavar='table_file')
    exclusive_group = firmware_parser.add_mutually_exclusive_group(required=True)
    exclusive_group.add_argument('-f', type=str, help='absolute path of the firmware dump file', metavar='fw_file')
    exclusive_group.add_argument('-d', type=str, help='absolute path of the directory containing multiple firmware dumps (execute for all dumps)', metavar='fw_dir')

    # define companion app subparser
    companion_app_str = 'Forensic examination of the persistent companion app data.'
    companion_app_parser = subparsers.add_parser('app', help=companion_app_str, description=companion_app_str)

    companion_app_parser.add_argument('-i', type=str, help='app id, if directory is renamed (optional)', metavar='id')
    companion_app_parser.add_argument('-a', type=str, required=True, help='path for the app data directory', metavar='dir')
    companion_app_parser.add_argument('-o', type=str, required=True, help='output path for the log and output files', metavar='path')

# define network subparser
    network_str = 'Analyze a network pcap file for forensically relevant traces.'
    network_parser = subparsers.add_parser('network', help=network_str, description=network_str)

    network_parser.add_argument('-k', type=str, help='absolute path of the ssl keylog file (optional)', metavar='keyfile')
    network_parser.add_argument('--ip', type=str, help='IP of device to filter for (optional)', metavar='ip_filter')
    network_parser.add_argument('-f', type=str, required=True, help='absolute path of the network traffic pcap file', metavar='file')
    network_parser.add_argument('-o', type=str, required=True, help='output path for the log and output files', metavar='path')

    # define remote subparser
    remote_str = 'Calls the device list from the given vendor cloud API for the given user credentials.'
    remote_parser = subparsers.add_parser('remote', help=remote_str, description=remote_str)

    remote_parser.add_argument('-v', type=str, required=True, help='specifies the vendor cloud (possible values: shelly, ewelink, meross, tuya)', metavar='vendor')
    remote_parser.add_argument('-c', nargs=2, type=str, required=True, help='cloud credentials separated with a space, usually: mail pw (for tuya: id key)', metavar=('mail', 'pw'))
    remote_parser.add_argument('-o', type=str, required=True, help='output path for the log and output files', metavar='path')

    args = parser.parse_args()

    st = time.time()

    if args.sub_command == 'firmware':
        firmware(args)
    elif args.sub_command == 'app':
        companion_app(args)
    elif args.sub_command == 'network':
        network(args)
    elif args.sub_command == 'remote':
        remote(args)
    else:
        parser.print_help()

    duration = time.time() - st

    print('finished', 'duration:', str(datetime.timedelta(seconds=duration)))
    
if __name__ == '__main__':
    main()
