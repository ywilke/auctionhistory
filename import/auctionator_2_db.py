# Imports
import os
import sys
import re
import datetime
import time
import sqlite3 as sqlite

# Config
with open('work_dir.txt', 'r') as work_dir_file:  
    work_dir = work_dir_file.read() # Working dir
    os.chdir(work_dir)

with open('source_dir.txt', 'r') as source_dir_file:
    source_dir = source_dir_file.read() # Source dir

# Setup code
if not os.path.exists("AH_history.db"):
    open("AH_history.db","w").close()
if not os.path.exists("import.log"):
    open("import.log","w").close()
if not os.path.exists("last_scan.txt"):
    open("last_scan.txt","w").close()

#open db
con = sqlite.connect('AH_history.db')
cur = con.cursor()

# Create Tables
with con:    
        
    cur.execute("CREATE TABLE IF NOT EXISTS LOR_H_items("
                "itemid INTEGER PRIMARY KEY,"
                "itemname TEXT UNIQUE COLLATE NOCASE);")
        
    cur.execute("CREATE TABLE IF NOT EXISTS LOR_H_scans("
                "scanid INTEGER PRIMARY KEY,"
                "scantime INT UNIQUE);")
        
    cur.execute("CREATE TABLE IF NOT EXISTS LOR_H_prices("
                "priceid INTEGER PRIMARY KEY,"
                "price INT,"
                "itemid INT,"
                "scanid INT,"
                "FOREIGN KEY(scanid) REFERENCES LOR_H_scans(scanid),"
                "FOREIGN KEY(itemid) REFERENCES LOR_H_items(itemid));")

# Functies
def get_date(unix_time):# Converts unix time to ISO 8601 date.
    return datetime.datetime.fromtimestamp(int(unix_time)).strftime('%Y-%m-%d %H:%M:%S')

def write_scan_times(): # Writes scan time
    try:
        time_file = open("scan_times.txt","a")
        time_file.write('{}\t{}\t{} entries\n'.format(current_scantime,get_date(current_scantime),len(sql_params)))
    finally:
        pass

def quit_script(print_message):
    con.rollback()
    con.close()
    print (print_message)
    print ('Aborting in 5 seconds')
    time.sleep(5)
    sys.exit(1)


# Importing
with open('{}Auctionator.lua'.format(source_dir)) as import_file:
    for line in import_file:
        line = line.rstrip()
        
        if line.split(' ')[0] == 'AUCTIONATOR_LAST_SCAN_TIME': # Gets the time of last scan
            current_scantime = int(line.split(' ')[2])
            cur.execute("SELECT MAX(scantime) FROM LOR_H_scans;")
            last_scan_time = cur.fetchone()[0]
            if not last_scan_time:
                last_scan_time = 0
                
            if current_scantime - last_scan_time <= 21600: # or 1==1
                quit_script('Less than 6 hours between scans. Prices not imported')
            elif current_scantime - last_scan_time > 21600:
                    cur.execute("INSERT INTO LOR_H_scans (scantime) VALUES (?);", (current_scantime,))
            else:
                quit_script('Unknown problem while comparing scantimes')
                
            break
        
with open('{}Auctionator.lua'.format(source_dir)) as import_file:
    importing = False
    sql_params = []
    for line in import_file:
        line = line.rstrip()
        
        if importing == False:
            if line == '	["Lordaeron_Horde"] = {':
                importing = True # Starts import at first item
        elif importing == True:
            if line == "	},":
                break
            else:
                match = re.match('\t\t\[\"([^].]+)\] = (\d+),',line)
                item = match.group(1)[:-1]
                price = int(match.group(2))
                sql_params.append((price, item, current_scantime))

cur.executemany('INSERT OR IGNORE INTO LOR_H_items (itemname) VALUES (?)',((sql_param[1],)for sql_param in sql_params))

cur.executemany("INSERT INTO LOR_H_prices (price, itemid, scanid) "
                "SELECT ?, sub.itemid, sub.scanid "
                "FROM ("
                    "SELECT LOR_H_items.itemid, LOR_H_scans.scanid "
                    "FROM LOR_H_items, LOR_H_scans "
                    "WHERE LOR_H_items.itemname = ? "
                    "AND LOR_H_scans.scantime = ? "
                ") sub;", sql_params)

con.commit()
con.close()
write_scan_times()