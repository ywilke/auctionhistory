import pyautogui
import psutil
import time
import datetime
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

wotlk_path = Path(cfg['DEFAULT']['wotlk_path'])
tbc_path = Path(cfg['DEFAULT']['tbc_path'])
realm_path = Path(wotlk_path / 'Data' / 'enUS')
wow_cfg_path = Path(wotlk_path / 'WTF')

prompt_timeout = int(cfg['scan']['prompt_timeout'])
prompt_delay = int(cfg['scan']['prompt_delay'])

known_hosts_path = Path(cfg['sftp']['known_hosts_path'])
sftp_user = cfg['sftp']['sftp_user']
sftp_pass = cfg['sftp']['sftp_password']
sftp_ip = cfg['sftp']['sftp_ip']
sftp_dir = PurePosixPath(cfg['sftp']['sftp_dir'])

SERVER_LIST = [
    {
        "server": 'warmane',
        "realmlist": 'logon.warmane.com',
        "realms": [
            {
                "realm": 'Lordaeron',
                "realmpos": (944, 267),
                "auc_pos_A": (1009, 441),
                "auc_pos_H": (958, 311),
            },
            {
                "realm": 'Icecrown',
                "realmpos": (949, 296),
                "auc_pos_A": (1009, 251),
                "auc_pos_H": (966, 326)
            }
        ],
        "user": cfg['warmane']['user'],
        "pass": cfg['warmane']['pass'],
        "auctionator": Path(cfg['warmane']['auctionator'])
    },
    {
        "server": 'gamerdistrict',
        "realmlist": 'wotlk.gamer-district.org',
        "realms": [
            {
                "realm": 'Echoes 1x',
                "realmpos": (953, 269),
                "auc_pos_A": (930, 446),
                "auc_pos_H": (983, 274)
            }
        ],
        "user": cfg['gamerdistrict']['user'],
        "pass": cfg['gamerdistrict']['pass'],
        "auctionator": Path(cfg['gamerdistrict']['auctionator'])
    }
]

CORDS = {
    "user" : (943, 565),
    "change_realm" : (1734, 72),
    "alliance" : (1687, 146), # char1
    "horde" : (1657, 228), # char2
    "scan" : (712, 159),
    "start_scan" : (506, 282),
    "quit" : (1812, 1010),
    "check_login": (100, 65, 280, 120),
    "check_scan": (240, 265, 350, 290),
    "check_game": (30, 965, 200, 1010),
    "check_spawn": (920, 1045, 950, 1070)
}
###############################################################################

def start_scan_prompt(timeout_after: 'Timeout for prompt in sec' = 120,
                      delay: 'Delay between next prompt in sec' = 3600):
    
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
    with open('debug.log','a') as debug_f:
        time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        debug_f.write(f"{time} {message}\n")


def start_wow(wow_path):
    subprocess.Popen(str(wow_path / 'Wow.exe'))
    img_check('check_game', 10)
    time.sleep(3)
    if wow_running() == True:
        return True
    else:
        print ('Wow did not start in time.')#TODO write debug
        sys.exit(1)


def wow_running():
    for proc in psutil.process_iter():
        if proc.name() == 'Wow.exe':
            return True
    return False


def login_wow(username, password):
    pyautogui.click(CORDS['user'], duration=1, tween=pyautogui.easeOutQuad) # Click username
    pyautogui.typewrite(username) # Type username
    pyautogui.press('tab')
    time.sleep(1)
    pyautogui.typewrite(password) # Type password
    time.sleep(1)
    pyautogui.press('enter') # Login
    img_check('check_login', 20)
    time.sleep(2)


def img_check(image, tries):
    box = CORDS[image]
    i = 0
    im1 = Image.open(f'img/{image}.png')
    im1 = np.array(im1)
    im2 = ImageGrab.grab(box)
    im2 = np.array(im2)
    time.sleep(3)# remove
    while np.array_equal(im1, im2) != True and i <= tries:
        print (i)
        time.sleep(6)
        i += 1
        im2 = ImageGrab.grab(box)
        im2 = np.array(im2)
    if i >= tries:
        write_debug(f'ERROR: {image} took too long to complete')
    return


def clean_auctionator(auctionator_path):
    with open(auctionator_path / 'Auctionator.lua', 'r') as f:
        lines = f.readlines()
    with open(auctionator_path / 'Auctionator.lua', 'w') as f:
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

   
def scan_auction(faction, auc_pos):
    pyautogui.click(CORDS[faction], duration=2, tween=pyautogui.easeOutQuad) # Select character
    pyautogui.press('enter') # Enter world
    img_check('check_spawn', 20) # Wait for world to load
    time.sleep(5)
    pyautogui.click(auc_pos, duration=1, tween=pyautogui.easeOutQuad, button='right') # Click auctioneer
    pyautogui.click(CORDS['scan'], duration=3, tween=pyautogui.easeOutQuad) # Open scan
    pyautogui.click(CORDS['start_scan'], duration=2, tween=pyautogui.easeOutQuad) # Start scan
    img_check('check_scan', 100) # Wait for scan to complete
    pyautogui.press('esc', 3, 0.2)
    pyautogui.press('enter') # Open chat
    pyautogui.typewrite('/logout') # Logout
    pyautogui.press('enter')
    time.sleep(5)
    return


def change_realm(realm_pos):
    pyautogui.click(CORDS['change_realm'], duration=2, tween=pyautogui.easeOutQuad) # Open realm select
    pyautogui.click(realm_pos, clicks=2, interval=0.2, duration=5, tween=pyautogui.easeOutQuad) # Select realm
    time.sleep(7)
    return


def change_realmlist(server):
    realmlist = server['realmlist']
    with open(realm_path / 'realmlist.wtf', 'w') as realmlist_f:
        realmlist_f.write(f"set realmlist {realmlist}")
    realm = server['realms'][0]['realm']
    with open(wow_cfg_path / 'Config.wtf', 'r+') as cfg_file:
        lines = cfg_file.readlines()
        for i, line in enumerate(lines):
            if line.split(' ')[1] == 'realmName':
                lines[i] = f'SET realmName "{realm}"\n'
                break
        cfg_file.seek(0)
        cfg_file.writelines(lines)


def playing_wow():
    if wow_running() == True:
        time.sleep(1800)
        return True
    else:
        return False


def stop_wow():
    pyautogui.click(CORDS['quit'], duration=2, clicks=2, interval=5) # Quit WoW
    time.sleep(5)
    
    for proc in psutil.process_iter(): # Stop wow if still running
        if proc.name() == 'Wow.exe':
            proc.kill()
            time.sleep(5)   
    return


def upload_auc_file(server):
    cnopts = pysftp.CnOpts(knownhosts=known_hosts_path)
    cnopts.log = 'sftp.log'
    with pysftp.Connection(host=sftp_ip, username=sftp_user, password=sftp_pass, cnopts=cnopts) as sftp_server:
        cwd_path = str(sftp_dir / f"{server['server']}")
        try:
            sftp_server.cwd(cwd_path)
            sftp_server.remove('Auctionator.lua')
            sftp_server.put(server['auctionator'] / 'Auctionator.lua')
        except IOError as e:
            write_debug(f"str(e) {server['server']}")
        finally:
            if sftp_server.isfile('Auctionator.lua') == False:
                write_debug(f"ERROR: Uploaded file not found! {server['server']}")


def main():
    for server in SERVER_LIST:
        change_realmlist(server)
        clean_auctionator(server['auctionator'])
        start_wow(wotlk_path)
        login_wow(username=server['user'], password=server['pass'])
        for realm in server['realms']:
            if len(server['realms']) > 1:
                change_realm(realm['realmpos'])
            scan_auction(faction="alliance", auc_pos=realm["auc_pos_A"])
            scan_auction(faction="horde", auc_pos=realm["auc_pos_H"])    
        stop_wow()
        upload_auc_file(server)
    change_realmlist(SERVER_LIST[0]) # Change realm list back
    scan2db.main() # import to db

    
if __name__ == "__main__":
    if start_scan_prompt(prompt_timeout,prompt_delay) == True:
        main()
