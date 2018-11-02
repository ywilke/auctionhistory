import pyautogui
import psutil
import time
import datetime
import pickle
import sys
import numpy as np
import configparser
import subprocess
import scan2db
from pathlib import Path, PurePosixPath
import pysftp
from PIL import ImageGrab, Image
# cfg and variable setup
###############################################################################
cfg = configparser.ConfigParser()
cfg.read('import.cfg')

SERVER_LIST = pickle.load(open('../SERVER_LIST.p', 'rb'))
EXP = pickle.load(open('../EXP.p', 'rb'))
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


def start_wow(server):
    '''Starts the World of warcraft client for the right expansion'''
    expan = server['expansion']
    subprocess.Popen(str(EXP[expan]['path'] / 'Wow.exe'))
    img_check('ss_game', server)
    time.sleep(3)
    return


def login_wow(server):
    '''Login on the wow client'''
    expan = server['expansion']
    pyautogui.click(EXP[expan]['user'], duration=1, tween=pyautogui.easeOutQuad) # Click username
    pyautogui.typewrite(server['user']) # Type username
    pyautogui.press('tab')
    time.sleep(1)
    pyautogui.typewrite(server['pass']) # Type password
    time.sleep(1)
    pyautogui.press('enter') # Login
    img_check('ss_home', server)
    time.sleep(2)


def img_check(state, server, realm_obj=None):
    '''Checks a part of screen for a known image or difference'''
    expan = server['expansion']
    data = EXP[expan][state]
    image = data['image']
    tries = data['tries']
    task = data['task']
    box = data['box']
    if realm_obj != None:
        realm = realm_obj['name']
    else:
        realm = None
    i = 0
    if task == 'match':
        im1 = Image.open(f'img1080/{image}.png')
        im1 = np.array(im1)
        im2 = ImageGrab.grab(box)
        im2 = np.array(im2)
        while np.array_equal(im1, im2) != True and i <= tries: # Check against known img
            print (i)
            time.sleep(6)
            i += 1
            im2 = ImageGrab.grab(box)
            im2 = np.array(im2)
    elif task == 'diff':
        im1 = np.array(1)
        im2 = np.array(2)
        while np.array_equal(im1, im2) != True and i <= tries: # Check if the scan progress stops
            mult = 6
            im1 = ImageGrab.grab(box)
            im1 = np.array(im1)
            print (i)
            time.sleep(6*mult)
            i += 1*mult
            im2 = ImageGrab.grab(box)
            im2 = np.array(im2)
        time.sleep(15) # Time to process
    if i > tries:
        write_debug(f'ERROR: {state} on {server["server"]}:{realm} took too long to complete')
    return


def clean_scandata(server):
    '''Clean old scandata'''
    if server['scan'] == 'auctionator_wotlk':
        with open(server['savedvar'] / 'Auctionator.lua', 'r') as f:
            lines = f.readlines()
        with open(server['savedvar'] / 'Auctionator.lua', 'w') as f:
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
    elif server['scan'] == 'auctioneer_wotlk' or server['scan'] == 'auctioneer_tbc':
        with open(server['savedvar'] / 'Auc-ScanData.lua', 'w') as f:
            f.write('')
        time.sleep(1)   

   
def scan_auction(server, realm_obj, faction):
    '''Execute an auction house scan'''
    expan = server['expansion']
    pyautogui.click(EXP[expan][f'char_{faction}'], duration=2, tween=pyautogui.easeOutQuad) # Select character
    pyautogui.press('enter') # Enter world
    img_check('ss_spawn', server, realm_obj) # Wait for world to load
    time.sleep(5)
    pyautogui.click(realm_obj[f'auc_pos_{faction}'], duration=1, tween=pyautogui.easeOutQuad, button='right') # Click auctioneer
    if server['scan'] == 'auctioneer_tbc' or server['scan'] == 'auctioneer_wotlk':
        pyautogui.click(EXP[expan]['auctioneer'], duration=3, tween=pyautogui.easeOutQuad) # Start scan
        img_check('ss_auctioneer', server, realm_obj)
    elif server['scan'] == 'auctionator_wotlk':
        pyautogui.click(EXP[expan]['auctionator'], duration=3, tween=pyautogui.easeOutQuad) # Open scan
        pyautogui.click(EXP[expan]['auctionator_start'], duration=2, tween=pyautogui.easeOutQuad) # Start scan
        img_check('ss_auctionator', server, realm_obj) # Wait for scan to complete      
    pyautogui.press('esc', 3, 0.2)
    pyautogui.press('enter') # Open chat
    pyautogui.typewrite('/logout') # Logout
    pyautogui.press('enter')
    time.sleep(5)
    return


def change_realm(server, realm_obj):
    '''Change realm in-game'''
    expan = server['expansion']
    pyautogui.click(EXP[expan]['change_realm'], duration=2, tween=pyautogui.easeOutQuad) # Open realm select
    pyautogui.click(realm_obj['realmpos'], clicks=2, interval=0.2, duration=5, tween=pyautogui.easeOutQuad) # Select realm
    time.sleep(7)
    return


def change_realmlist(server):
    '''Change realmlist and set default realm'''
    realmlist = server['realmlist']
    expan = server['expansion']
    base_path = EXP[expan]['path']
    with open(base_path / EXP[expan]['realm_path'] / 'realmlist.wtf', 'w') as realmlist_f:
        realmlist_f.write(f"set realmlist {realmlist}")
    realm = server['realms'][0]['realm']
    with open(base_path / EXP[expan]['cfg_path'] / 'Config.wtf', 'r+') as cfg_file:
        lines = cfg_file.readlines()
        for i, line in enumerate(lines):
            if line.split(' ')[1] == 'realmName':
                lines[i] = f'SET realmName "{realm}"\n'
                break
        cfg_file.seek(0)
        cfg_file.writelines(lines)


def stop_wow(server):
    '''Stops the world of warcraft client''' 
    expan = server['expansion']
    pyautogui.click(EXP[expan]['quit'], duration=2, clicks=2, interval=5) # Quit WoW
    time.sleep(5)
    for proc in psutil.process_iter(): # Stop wow if still running
        if proc.name() == 'Wow.exe':
            proc.kill()
            time.sleep(5)   
    return


def upload_auc_file(server):
    '''Upload scan files to remote server'''
    known_hosts_path = Path(cfg['sftp']['known_hosts_path'])
    sftp_user = cfg['sftp']['sftp_user']
    sftp_pass = cfg['sftp']['sftp_password']
    sftp_ip = cfg['sftp']['sftp_ip']
    sftp_dir = PurePosixPath(cfg['sftp']['sftp_dir'])
    cnopts = pysftp.CnOpts(knownhosts=known_hosts_path)
    cnopts.log = 'sftp.log'
    with pysftp.Connection(host=sftp_ip, username=sftp_user, password=sftp_pass, cnopts=cnopts) as sftp_server:
        cwd_path = str(sftp_dir / f"{server['server']}")
        try:
            sftp_server.cwd(cwd_path)
            if server['scan'] == 'auctioneer_tbc' or server['scan'] == 'auctioneer_wotlk':
                try:
                    sftp_server.remove('Auc-ScanData.lua')
                except IOError:
                    pass
                sftp_server.put(server['savedvar'] / 'Auc-ScanData.lua')
                if sftp_server.isfile('Auc-ScanData.lua') == False:
                    write_debug(f"ERROR: Uploaded file not found! {server['server']}")
            elif server['scan'] == 'auctionator_wotlk':
                try:
                    sftp_server.remove('Auctionator.lua')
                except IOError:
                    pass
                sftp_server.put(server['savedvar'] / 'Auctionator.lua')
                if sftp_server.isfile('Auctionator.lua') == False:
                    write_debug(f"ERROR: Uploaded file not found! {server['server']}")
        except IOError as e:
            write_debug(f"IOError: {str(e)} {server['server']}")


def main():
    for server in SERVER_LIST:
        change_realmlist(server)
        clean_scandata(server)
        start_wow(server)
        login_wow(server)
        for realm_obj in server['realms']:
            if server['realms'][0]['name'] != realm_obj['name']: # Switch realm if not first realm
                change_realm(server, realm_obj)
            scan_auction(server, realm_obj, 'A')
            scan_auction(server, realm_obj, 'H')    
        stop_wow(server)
        upload_auc_file(server)
    change_realmlist(SERVER_LIST[0]) # Change realm list back
    scan2db.main()

   
if __name__ == "__main__":
    prompt_timeout = int(cfg['scan']['prompt_timeout'])
    prompt_delay = int(cfg['scan']['prompt_delay'])
    if start_scan_prompt(prompt_timeout,prompt_delay) == True:
        main()