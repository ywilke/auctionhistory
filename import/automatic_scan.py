import time
import sys
import pickle
import subprocess
import configparser
from pathlib import Path, PurePosixPath
from PIL import ImageGrab, Image

import requests
import win32gui
import pyautogui
import psutil
import datetime
import numpy as np
import pysftp

import scan2db


# cfg and variable setup
###############################################################################
cfg = configparser.ConfigParser()
cfg.read('import.cfg')

SERVER_LIST = pickle.load(open('../SERVER_LIST.p', 'rb'))
EXP = pickle.load(open('../EXP.p', 'rb'))
RANDID = pickle.load(open('../RANDID.p', 'rb'))
###############################################################################
def start_scan_prompt(timeout_after: 'Timeout for prompt in sec' = 120,
                      delay: 'Delay between next prompt in sec' = 3600):
    '''Prompt to start the scan'''
    delay_m = int(delay/60) 
    button = pyautogui.confirm(text = 'Do you want to start the auction house scan?',
                               title = 'Auction House Scanner',
                               buttons = ['Start!','Delay ({}m)'.format(delay_m), 'Cancel'],
                               timeout = (timeout_after*1000))
    if button == 'Delay ({}m)'.format(delay_m):
        time.sleep(delay)
        if start_scan_prompt(timeout_after, delay) == True:
            return True
    elif button == 'Cancel':
        sys.exit(0)
    elif button == 'Start!' or button == 'Timeout':
        return True


def write_debug(message):
    '''Write a message to the debug log'''
    with open('debug.log','a') as debug_f:
        stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        debug_f.write(f"{stamp} {message}\n")


def start_wow(server_obj):
    '''Starts the World of warcraft client for the right expansion'''
    expan = server_obj['expansion']
    subprocess.Popen(str(EXP[expan]['path'] / 'Wow.exe'))
    if expan == 'clas':
        time.sleep(5)
        pyautogui.click((1062, 590))
        time.sleep(5)
        window = win32gui.FindWindow(None, 'World of Warcraft')
        win32gui.SetForegroundWindow(window)
    img_check('ss_game', server_obj)
    time.sleep(3)
    return


def login_wow(server_obj, fac):
    '''Login on the wow client'''
    expan = server_obj['expansion']
    pyautogui.click(EXP[expan]['user'], duration=1, tween=pyautogui.easeOutQuad) # Click username
    username = server_obj['user']
    if server_obj['realms'][0]['name'] in ['Nightbane', 'Netherwing'] and fac == 'H':
        username = username.replace('1', '2')
    pyautogui.typewrite(username) # Type username
    pyautogui.press('tab')
    time.sleep(1)
    pyautogui.typewrite(server_obj['pass']) # Type password
    time.sleep(1)
    pyautogui.press('enter') # Login
    img_check('ss_home', server_obj)
    time.sleep(2)


def img_check(state, server_obj, realm_obj=None, fac=None):
    '''Checks a part of screen for a known image or difference'''
    expan = server_obj['expansion']
    data = EXP[expan][state]
    image = data['image']
    tries = data['tries']
    task = data['task']
    box = data['box']
    if realm_obj != None:
        realm = realm_obj['name']
    else:
        realm = None
    print (f'img check {state} for {server_obj["server"]}:{realm}:{fac}')
    i = 0
    if task == 'match':
        im1 = np.array(Image.open(f"img/{cfg['scan']['img']}/{image}.png"))
        im2 = np.array(ImageGrab.grab(box))
        while np.array_equal(im1, im2) != True and i <= tries: # Check against known img
            print (i)
            time.sleep(6)
            i += 1
            im2 = np.array(ImageGrab.grab(box))
    elif task == 'diff': # Checks if scan is progressing and if player is still spawned in
        im3 = np.array(Image.open(f"img/{cfg['scan']['img']}/{expan}_spawn.png"))
        spawn_box = EXP[expan]['ss_spawn']['box']
        im1 = np.array(1)
        im2 = np.array(2)
        while np.array_equal(im1, im2) != True and i <= tries: # Check if the scan progress stops
            mult = 50
            im1 = np.array(ImageGrab.grab(box))
            print (i)
            time.sleep(6*mult)
            i += 1*mult
            im2 = np.array(ImageGrab.grab(box))
            im4 = np.array(ImageGrab.grab(spawn_box))
            pyautogui.press('space')
            if np.array_equal(im3, im4) != True:
                write_debug(f'ERROR: {state} on {server_obj["server"]}:{realm}:{fac} failed spawn img check')
                return False
        time.sleep(15) # Time to process
    if i > tries:
        write_debug(f'ERROR: {state} on {server_obj["server"]}:{realm}:{fac} took too long to complete')
        return False
    return True


def clean_scandata(server_obj):
    '''Clean old scandata'''
    if server_obj['scan'] == 'auctionator_wotlk':
        with open(server_obj['savedvar'] / 'Auctionator.lua', 'r') as f:
            lines = f.readlines()
        with open(server_obj['savedvar'] / 'Auctionator.lua', 'w') as f:
            delete = False
            for line in lines:
                if delete == False:
                    if line == 'AUCTIONATOR_PRICING_HISTORY = {\n' or line == 'AUCTIONATOR_PRICE_DATABASE = {\n':
                        delete = True
                    else:
                        f.write(line)
                elif delete == True:
                    if line == '}\n':
                        delete = False
                    else:
                        pass
        return
    
    elif server_obj['scan'] == 'auctioneer_wotlk' or server_obj['scan'] == 'auctioneer_tbc':
        with open(server_obj['savedvar'] / 'Auc-ScanData.lua', 'w') as f:
            f.write('')
        if server_obj['realms'][0]['name'] in ['Nightbane', 'Netherwing']:
            path = Path(str(server_obj['savedvar'] / 'Auc-ScanData.lua').replace('1', '2'))
            print (path)
            with open(path, 'w') as f:
                f.write('')
            
        return
    
    elif server_obj['scan'] == 'auctioneer_clas':
        with open(server_obj['savedvar'] / 'Auctioneer.lua', 'w') as f:
            f.write('')
        return
    

   
def scan_auction(server_obj, realm_obj, faction):
    '''Execute an auction house scan'''
    expan = server_obj['expansion']
    pyautogui.click(EXP[expan][f'char_{faction}'], duration=2, tween=pyautogui.easeOutQuad) # Select character
    pyautogui.press('enter') # Enter world
    img_check('ss_spawn', server_obj, realm_obj, faction) # Wait for world to load
    time.sleep(15)
    pyautogui.click(realm_obj[f'auc_pos_{faction}'], duration=1, tween=pyautogui.easeOutQuad, button='right', clicks=5, interval=1) # Click auctioneer
    time.sleep(5)
    if server_obj['scan'] == 'auctioneer_clas' or server_obj['scan'] == 'auctioneer_tbc' or server_obj['scan'] == 'auctioneer_wotlk':
        pyautogui.click(EXP[expan]['auctioneer'], duration=1, tween=pyautogui.easeOutQuad) # Start scan
        success = img_check('ss_auctioneer', server_obj, realm_obj, faction)
    elif server_obj['scan'] == 'auctionator_wotlk':
        pyautogui.click(EXP[expan]['auctionator'], duration=1, tween=pyautogui.easeOutQuad) # Open scan
        pyautogui.click(EXP[expan]['auctionator_start'], duration=4, tween=pyautogui.easeOutQuad) # Start scan
        success = img_check('ss_auctionator', server_obj, realm_obj, faction) # Wait for scan to complete
    pyautogui.press('esc', 3, 0.2)
    pyautogui.press('enter') # Open chat
    pyautogui.typewrite('/logout') # Logout
    pyautogui.press('enter')
    time.sleep(10)
    if server_obj['scan'] == 'auctioneer_clas':
        with open(server_obj['savedvar'] / 'Auctioneer.lua', 'a') as scan_file:
            scan_file.write(f"\nscantime = {int(time.time())}\n")
    return success


def change_realm(server_obj, realm_obj):
    '''Change default realm on game start'''
    realm = realm_obj['realm']
    expan = server_obj['expansion']
    base_path = EXP[expan]['path']
    with open(base_path / EXP[expan]['cfg_path'] / 'Config.wtf', 'r+') as cfg_file:
        lines = cfg_file.readlines()
        for i, line in enumerate(lines):
            if line.split(' ')[1] == 'realmName':
                lines[i] = f'SET realmName "{realm}"\n'
                break
        cfg_file.seek(0)
        cfg_file.writelines(lines)
    return


def change_realmlist(server_obj):
    '''Change realmlist and set default realm'''
    realmlist = server_obj['realmlist']
    expan = server_obj['expansion']
    base_path = EXP[expan]['path']
    with open(base_path / EXP[expan]['realm_path'] / 'realmlist.wtf', 'w') as realmlist_f:
        realmlist_f.write(f"set realmlist {realmlist}")
    return


def stop_wow(server_obj):
    '''Stops the world of warcraft client''' 
    expan = server_obj['expansion']
    pyautogui.click(EXP[expan]['quit'], duration=2, clicks=2, interval=5) # Quit WoW
    time.sleep(5)
    for proc in psutil.process_iter(): # Stop wow if still running
        if proc.name() in ['Wow.exe', 'WoW.exe']:
            proc.kill()
            time.sleep(10)   
    return


def upload_auc_file(server_obj):
    '''Upload scan files to remote server'''
    expan = server_obj['expansion']
    known_hosts_path = Path(cfg['sftp']['known_hosts_path'])
    sftp_user = cfg['sftp']['sftp_user']
    sftp_pass = cfg['sftp']['sftp_password']
    sftp_ip = cfg['sftp']['sftp_ip']
    sftp_dir = PurePosixPath(cfg['sftp']['sftp_dir'])
    cnopts = pysftp.CnOpts(knownhosts=known_hosts_path)
    cnopts.log = 'sftp.log'
    with pysftp.Connection(host=sftp_ip, username=sftp_user, password=sftp_pass, cnopts=cnopts) as sftp_server:
        cwd_path = str(sftp_dir / f"{server_obj['server']}/{expan}")
        try:
            sftp_server.cwd(cwd_path)
            if server_obj['scan'] == 'auctioneer_tbc' or server_obj['scan'] == 'auctioneer_wotlk':
                data_file = 'Auc-ScanData.lua'
            elif server_obj['scan'] == 'auctionator_wotlk':
                data_file = 'Auctionator.lua'
            elif server_obj['scan'] == 'auctioneer_clas':
                data_file = 'Auctioneer.lua'
            elif server_obj['scan'] == 'api':
                data_file = 'scandata.p'
            try:
                sftp_server.remove(data_file)
            except IOError:
                pass
            sftp_server.put(server_obj['savedvar'] / data_file)
            if sftp_server.isfile(data_file) == False:
                write_debug(f"ERROR: Uploaded file not found! {server_obj['server']}")
        except Exception as e:
            write_debug(f"Exception during upload: {str(e)} for server {server_obj['server']}")


def merge_scandata(server_obj):
    try:
        with open(server_obj['savedvar'] / 'Auc-ScanData.lua', 'a') as scan_file_1, \
                open(str(server_obj['savedvar'] / 'Auc-ScanData.lua').replace('1', '2'), 'r') as scan_file_2:
            scan_data_2 = scan_file_2.read()
            scan_file_1.write(scan_data_2)
    except Exception as e:
        write_debug(f'{e}: while merging scan data files')


def api_scan(server_obj):
    if server_obj['server'] == 'tauri':
        URL = 'http://chapi.tauri.hu/apiIndex.php'
        api_param = {'apikey': str(cfg['tauri']['user'])}
        payload= {
            'secret': str(cfg['tauri']['pass']),
            'url': 'auctions-data',
            'params': {
                'r': '[HU] Tauri WoW Server',
            }
        }
        r = requests.post(URL, params=api_param, json=payload)
        if r.status_code != requests.codes.ok:
            write_debug(f"API request for {server_obj['server']} failed with status code {r.status_code}")
            return
        response = r.json()
        if response['success'] != True:
            write_debug(f"API resonse contains errorcode {response['errorcode']}: {response['errorstring']}")
            return
        realm = server_obj['realms'][0]['name']
        auc_data = response['response']['auctions']
        ahs = {"auctioner_2": 'Alliance',
               "auctioner_6": 'Horde',
               "auctioner_7": None}
        data = {}
        scantime = 0
        low_price = {}
        scantime = int(response['response']['lastModified'])
        for ah in auc_data:
            if ahs[ah] == None:
                continue
            rf = f"{realm}_{ahs[ah]}"
            data[rf] = []
            low_price[rf] = {}
            for auc in auc_data[ah]:
                raw_name = auc['itemData']['itemName']
                raw_id = str(auc['item'])
                rand_id = str(auc['rand'])
                price = int(auc['buyout'] / auc['stackCount'])
                if price == 0:
                    continue
                if rand_id != '0':
                    item_name = f"{raw_name} {RANDID[rand_id]}"
                    item_id = f"{raw_id}:{rand_id}"
                else:
                    item_name = raw_name
                    item_id = f"{raw_id}:0"
                try:
                    if price < low_price[rf][item_name][0]:
                        low_price[rf][item_name] = (price, item_id)
                except KeyError:
                    low_price[rf][item_name] = (price, item_id)
        for rf in low_price:
            for item in low_price[rf]:
                data[rf].append((low_price[rf][item][0], item, low_price[rf][item][1]))
        scandata_obj = {'data': data,
                         'scantime': scantime}
        pickle.dump(scandata_obj, open(server_obj['savedvar'] / 'scandata.p', 'wb'))
        return
            

def main():
    failed = {'A': [], 'H': []}
    for server_obj in SERVER_LIST:
        if server_obj['scan'] == 'api':
            api_scan(server_obj)
            continue
        change_realmlist(server_obj)
        clean_scandata(server_obj)
        for realm_obj in server_obj['realms']:
            change_realm(server_obj, realm_obj)
            for fac in ['A', 'H']:
                start_wow(server_obj)
                login_wow(server_obj, fac)
                success = scan_auction(server_obj, realm_obj, fac)
                if success == False:
                    failed[fac].append(realm_obj['name'])
                stop_wow(server_obj)

    for server_obj in SERVER_LIST:
        for realm_obj in server_obj['realms']:
            for fac in ['A', 'H']:
                if realm_obj['name'] in failed[fac]:
                    change_realmlist(server_obj)
                    change_realm(server_obj, realm_obj)
                    start_wow(server_obj)
                    login_wow(server_obj, fac)
                    success = scan_auction(server_obj, realm_obj, fac)
                    write_debug(f'Rescan of {realm_obj["name"]}:{fac} returned {success}')
                    stop_wow(server_obj)
        if server_obj['realms'][0]['name'] in ['Nightbane', 'Netherwing']:
            merge_scandata(server_obj)
        upload_auc_file(server_obj)
    scan2db.main() # Import scandata


if __name__ == "__main__":
    prompt_timeout = int(cfg['scan']['prompt_timeout'])
    prompt_delay = int(cfg['scan']['prompt_delay'])
    if start_scan_prompt(prompt_timeout,prompt_delay) == True:
        main()

    