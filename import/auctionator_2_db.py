# Imports
import os
import sys
import re
import datetime
import time
import sqlite3 as sqlite
import configparser

# Functions
def fix_path(path):
    py_path = path.replace('\\','/')
    try:
        if py_path[(len(py_path))-1] != '/':
            py_path += '/'
            return py_path
    except IndexError:
        return None

def get_date(unix_time):# Converts unix time to ISO 8601 date.
    return datetime.datetime.fromtimestamp(int(unix_time)).strftime('%Y-%m-%d %H:%M:%S')

def quit_script(print_message, con):
    con.rollback()
    con.close()
    print (print_message)
    print ('Aborting in 5 seconds')
    time.sleep(5)
    sys.exit(1)

def main(auctionator_path):
    
    # Create DB file
    if not os.path.exists("AH_history.db"):
        open("AH_history.db","w").close()
    
    # Connect to DB
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

    # Importing
    with open('{}Auctionator.lua'.format(auctionator_path)) as import_file:
        for line in import_file:
            line = line.rstrip()
            
            if line.split(' ')[0] == 'AUCTIONATOR_LAST_SCAN_TIME': # Gets the time of last scan
                current_scantime = int(line.split(' ')[2])
                cur.execute("SELECT MAX(scantime) FROM LOR_H_scans;")
                last_scan_time = cur.fetchone()[0]
                if not last_scan_time:
                    last_scan_time = 0
                    
                if current_scantime - last_scan_time <= 21600: # or 1==1
                    quit_script('Less than 6 hours between scans. Prices not imported', con)
                elif current_scantime - last_scan_time > 21600:
                        cur.execute("INSERT INTO LOR_H_scans (scantime) VALUES (?);", (current_scantime,))
                else:
                    quit_script('Unknown problem while comparing scantimes', con)
                    
                break
            
    with open('{}Auctionator.lua'.format(auctionator_path)) as import_file:
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
                    match = re.match('\t\t\[\"(.+)\] = (\d+),',line)
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
    
    # Info to report
    cur.execute('SELECT count(price) FROM LOR_H_prices;')
    nr_prices = cur.fetchone()[0]
    cur.execute('SELECT count(itemid) FROM LOR_H_items;')
    nr_items = cur.fetchone()[0]
    
    # Finish
    con.close()
    with open("completed_scans.txt","a") as scans_file:
        scans_file.write('{date}\tPrices added: {scansize}\tDatabase now contains: {nr_items} items, {nr_prices} prices'.format(date = get_date(current_scantime), scansize = len(sql_params), nr_items = nr_items, nr_prices = nr_prices))
    return True
    
if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('import.cfg')
    auctionator_path = fix_path(config['DEFAULT']['auctionator_path'])
    if not auctionator_path:
        print ('Fill out auctionator path into import.cfg')
        sys.exit(1)
    main(auctionator_path)
    