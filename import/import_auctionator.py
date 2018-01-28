# Imports and settings
import os
import sys
import re
import datetime

work_dir = 'D:/Yano/Drive/github/AH_history/import/' # Working dir
os.chdir(work_dir) 
source_dir = 'D:/Games/WoW/WTF/Account/HELLBLOOD1/SavedVariables/' # Source dir

# Setup code
if not os.path.exists("auction_history.txt"):
    open("auction_history.txt","w").close()
if not os.path.exists("scan_times.txt"):
    open("scan_times.txt","w").close()
if not os.path.exists("last_scan.txt"):
    open("last_scan.txt","w").close()

# Functies
def save_history_dict(): # Write auction history dict to disk
    with open("auction_history.txt","w") as auction_history_file:
        auction_history_file.write(str(auction_history))

def get_date(unix_time):# Converts unix time to ISO 8601 date.
    return datetime.datetime.fromtimestamp(int(unix_time)).strftime('%Y-%m-%d %H:%M:%S')

def write_scan_times(): # Writes scan time
    try:
        time_file = open("scan_times.txt","a")
        last_scan_file = open ("last_scan.txt","w")
        last_scan_file.write(scan_time)
        time_file.write('{}\t{}\n'.format(scan_time,get_date(scan_time)))
    finally:
        pass

# Code
with open("auction_history.txt","r") as auction_history_file: # Load dict of auction history
    auction_history = {}
    try:
        auction_history = eval(auction_history_file.read())
    except SyntaxError:
        pass

# Importing
with open('{}Auctionator.lua'.format(source_dir)) as import_file:
    scan_time = 0
    for line in import_file:
        line = line.rstrip()
        if line.split(' ')[0] == 'AUCTIONATOR_LAST_SCAN_TIME': # Gets the time of last scan
            scan_time = line.split(' ')[2]
            try:
                with open("last_scan.txt","r") as last_scan_file:
                    if int(scan_time) <= int(last_scan_file.read()):
                        sys.exit(0)
            except ValueError:
                pass
            break
with open('{}Auctionator.lua'.format(source_dir)) as import_file:
    importing = False
    for line in import_file:
        line = line.rstrip()
        if importing == False:
            if line == '	["Lordaeron_Horde"] = {':
                importing = True # Starts import at first item
        elif importing == True:
            if line == "	},":
                importing = False # Ends import at final item
            else:
                match = re.match('\t\t\[\"([^].]+)\] = (\d+),',line)
                item = match.group(1)[:-1]
                price = match.group(2)
                if item not in auction_history:
                    auction_history[item] = [(scan_time,price)]
                elif item in auction_history:
                    auction_history[item].append((scan_time,price))
print (auction_history['Mithril Ore'])
write_scan_times()                 
save_history_dict()      