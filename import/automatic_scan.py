import pyautogui
import psutil
import time
import sys
import configparser
import subprocess
import auctionator_2_db

###############################################################################
# Config
def fix_path(path):
    py_path = path.replace('\\','/')
    try:
        if py_path[(len(py_path))-1] != '/':
            py_path += '/'
            return py_path
    except IndexError:
        return None

config = configparser.ConfigParser()
config.read('import.cfg')
wow_path = fix_path(config['DEFAULT']['wow_path'])
auctionator_path = fix_path(config['DEFAULT']['auctionator_path'])

prompt_timeout = int(config['scan']['prompt_timeout'])
prompt_delay = int(config['scan']['prompt_delay'])
wow_user = config['scan']['wow_username']
wow_pass = config['scan']['wow_password']

for i in [wow_path, auctionator_path, prompt_timeout, prompt_delay]:
    if not i:
        pyautogui.alert(text='Fill in all the fields of import.cfg', title='Error in config file', button='OK')
        sys.exit(1)

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
        start_scan_prompt(timeout_after, delay)
    elif button == 'Cancel':
        sys.exit(0)
    elif button == 'Start!' or button == 'Timeout':
        return True

def main():
    
    # Start WoW if not already running
    if wow_running() == False:
        start_wow()
    
    # Scan auction house
    time.sleep(5)
    pyautogui.click(x=943, y=565, duration=1, tween=pyautogui.easeOutQuad) # Click username
    pyautogui.typewrite(wow_user) # Type username
    pyautogui.press('tab')
    pyautogui.typewrite(wow_pass) # Type password
    pyautogui.press('enter')
    time.sleep(10)
    pyautogui.click(x=1653, y=467, duration=1, tween=pyautogui.easeOutQuad) # Select character
    pyautogui.press('enter')
    time.sleep(60)
    pyautogui.click(x=965, y=253, duration=1, tween=pyautogui.easeOutQuad, button='right') # Click auctioneer
    pyautogui.click(x=713, y=161, duration=1, tween=pyautogui.easeOutQuad) # Open scan
    pyautogui.click(x=509, y=281, duration=1, tween=pyautogui.easeOutQuad) # Start scan
    time.sleep(30)
    pyautogui.press('esc', 4, 0.2)
    pyautogui.click(x=960, y=613, duration=1, tween=pyautogui.easeOutQuad) # Exits game
    time.sleep(3)
    for proc in psutil.process_iter(): # Stop wow if still running
        if proc.name() == 'Wow.exe':
            proc.kill()
    
    # Import scan to DB
    auctionator_2_db.main(auctionator_path)
    # Check if import was succesful
    
    # Shutdown PC if needed
    shutdown = True
    for proc in psutil.process_iter():
        if proc.name() in ['KeePass.exe','firefox.exe']:
            shutdown = False
    
    
    

def start_wow():
    subprocess.Popen('{}Wow.exe'.format(wow_path))
    time.sleep(10)
    if wow_running() == True:
        return True
    else:
        print ('Wow did not start in time.')
        sys.exit(1)

def wow_running():
    for proc in psutil.process_iter():
        if proc.name() == 'Wow.exe':
            return True
    return False
    
if __name__ == "__main__":
    if start_scan_prompt(prompt_timeout,prompt_delay) == True:
        main()
