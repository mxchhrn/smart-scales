import asyncio
import os
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from teaid.teaidlib.common import functions_helper as fhelper


# source: https://albertogeniola.github.io/MerossIot/quick-start.html#listing-devices
async def list_devices(user: str, passwd: str, f_log: str) -> list:
    # set device name
    # dev_name = '07_meross'
    # dev_name = '08_meross'

    # set base url for api
    api_url = 'https://iotx-eu.meross.com'

    fhelper.write_message(f"Preparing HTTP client API...", f_log)
    # set up the HTTP client API from user-password
    http_api_client = await MerossHttpClient.async_from_user_password(api_base_url=api_url, email=user, password=passwd)

    # Setup and start the device manager
    fhelper.write_message(f"Preparing device manager...", f_log)
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()
    fhelper.write_message(f"Device manager started.", f_log)

    # Retrieve all the MSS310 devices that are registered on this account
    fhelper.write_message(f"Requesting device list...", f_log)
    await manager.async_device_discovery()
    device_list = manager.find_devices()
    fhelper.write_message(f"Response received.\nDevice list: {device_list}", f_log)

    # Close the manager and logout from http_api
    fhelper.write_message(f"Close device manger & logout...", f_log)
    manager.close()
    await http_api_client.async_logout()
    fhelper.write_message(f"Device manager closed.", f_log)

    return device_list


def main(username: str, password: str, f_log: str) -> dict:
    r = {}
    try:
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.get_event_loop()
        r['devices'] = loop.run_until_complete(list_devices(username, password, f_log))
        loop.stop()
    except RuntimeError:
        pass
    return r
