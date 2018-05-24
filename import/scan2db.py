# Imports
import os
import sys
import re
import datetime
import time
import sqlite3 as sqlite
import configparser
import random
from pathlib import Path

# Functions
def get_date(unix_time):# Converts unix time to ISO 8601 date.
    return datetime.datetime.fromtimestamp(int(unix_time)).strftime('%Y-%m-%d %H:%M:%S')

def quit_script(print_message, con):
    con.rollback()
    con.close()
    print (print_message)
    print ('Aborting in 5 seconds')
    time.sleep(5)
    sys.exit(1)

def count_auctions(server, auctionator_path):
    with open(auctionator_path / 'Auctionator.lua', 'r') as auc_file:
            counting = False
            count = 0
            for line in auc_file:
                line = line.rstrip()
                
                if counting == False:
                    if line == '	["{server}"] = {{'.format(server=server):
                        counting = True # Starts count at first item
                elif counting == True:
                    if line == "	},":
                        break
                    else:
                        count += 1
            return count

def main(auctionator_path):
    
    # Create DB file
    if not os.path.exists("auctionhistory.db"):
        open("auctionhistory.db","w").close()
    
    # Connect to DB
    con = sqlite.connect('auctionhistory.db')
    cur = con.cursor()  
    
    # Create Tables
    with con:    
            
        cur.execute("CREATE TABLE IF NOT EXISTS items("
                    "itemid INTEGER PRIMARY KEY,"
                    "itemname TEXT UNIQUE COLLATE NOCASE);")
            
        cur.execute("CREATE TABLE IF NOT EXISTS scans("
                    "scanid INTEGER PRIMARY KEY,"
                    "scantime INT UNIQUE);")

        cur.execute("CREATE TABLE IF NOT EXISTS servers("
                    "serverid INTEGER PRIMARY KEY,"
                    "servername TEXT UNIQUE);")

        cur.execute("CREATE TABLE IF NOT EXISTS prices("
                    "priceid INTEGER PRIMARY KEY,"
                    "price INT,"
                    "itemid INT,"
                    "scanid INT,"
                    "serverid INT,"
                    "FOREIGN KEY(scanid) REFERENCES scans(scanid),"
                    "FOREIGN KEY(itemid) REFERENCES items(itemid),"
                    "FOREIGN KEY(serverid) REFERENCES servers(serverid));")
        
        cur.execute("CREATE INDEX IF NOT EXISTS idx_item_server ON prices (itemid, serverid);")

    # Importing
    with open(auctionator_path / 'Auctionator.lua', 'r') as import_file:
        for line in import_file:
            line = line.rstrip()
            
            if line.split(' ')[0] == 'AUCTIONATOR_LAST_SCAN_TIME': # Gets the time of last scan
                current_scantime = int(line.split(' ')[2])
                cur.execute("SELECT MAX(scantime) FROM scans;")
                last_scan_time = cur.fetchone()[0]
                if not last_scan_time:
                    last_scan_time = 0
                    
                if current_scantime - last_scan_time <= 21600: 
                    quit_script('Less than 6 hours between scans. Prices not imported', con)
                elif current_scantime - last_scan_time > 21600:
                    insert_scantime = current_scantime + random.randint(-1800,1800)
                    cur.execute("INSERT INTO scans (scantime) VALUES (?);", (insert_scantime,))
                else:
                    quit_script('Unknown problem while comparing scantimes', con)
                    
                break
            
    with open(auctionator_path / 'Auctionator.lua', 'r') as import_file:
        importing = False
        sql_params = []
        for line in import_file:
            line = line.rstrip()
            
            if importing == False:
                servermatch = re.match('\t\["(Lordaeron_Horde|Lordaeron_Alliance|Icecrown_Horde|Icecrown_Alliance)"\] = {', line)
                if servermatch:
                    server = servermatch.group(1)
                    importing = True # Starts import at first item
            elif importing == True:
                if line == "	},":
                    server = None
                    importing = False
                else:
                    itemmatch = re.match('\t\t\[\"(.+)\] = (\d+),', line)
                    item = itemmatch.group(1)[:-1]
                    price = int(itemmatch.group(2))
                    sql_params.append((price, item, insert_scantime, server))
    '''    # Auctioneer TBC import (disabled: 0 prices)            
    with open(auctionator_path / 'Auctionator.lua', 'r') as import_file:
        lowest_price = {
                'Outland_Alliance' : {},
                'Outland_Horde' : {}
                }  
        
        server = None
        for line in import_file:
            line = line.rstrip()
            servermatch = re.match('\t\t\t\["(Alliance|Horde)"\] = {', line)
            if servermatch:
                server = 'Outland_{faction}'.format(faction = servermatch.group(1))
            elif line.split(' ')[0] == '\t\t\t\t["image"]':
                data = line.split('return {')
                data = data[1].split('},')
                for entry in data:
                    values = entry.split(',')
                    if len(values) == 28:
                        itemname = re.search('h\[(.+)\]', values[0]).group(1)
                        buyout = int(values[16])
                        stack = int(values[10])
                        price = int(buyout / stack)
                        if price == 0:
                            continue
                        if itemname not in lowest_price[server]:
                            lowest_price[server][itemname] = price
                        elif price < lowest_price[server][itemname]:
                            lowest_price[server][itemname] = price
                            
        for server in lowest_price:
            for item in lowest_price[server]:
                price = lowest_price[server][item]
                sql_params.append((price, item, insert_scantime, server))
    
    '''
    
    cur.executemany('INSERT OR IGNORE INTO items (itemname) VALUES (?)',((sql_param[1],)for sql_param in sql_params))
    
    cur.executemany('INSERT OR IGNORE INTO servers (servername) VALUES (?)',((sql_param[3],)for sql_param in sql_params))
    
    cur.executemany("INSERT INTO prices (price, itemid, scanid, serverid) "
                    "SELECT ?, sub.itemid, sub.scanid, sub.serverid "
                    "FROM ("
                        "SELECT items.itemid, scans.scanid, servers.serverid "
                        "FROM items, scans, servers "
                        "WHERE items.itemname = ? "
                        "AND scans.scantime = ? "
                        "AND servers.servername = ? "
                        ") sub;", sql_params)
    
    con.commit()

    # Info to report
    cur.execute('SELECT count(price) FROM prices;')
    nr_prices = cur.fetchone()[0]
    cur.execute('SELECT count(itemid) FROM items;')
    nr_items = cur.fetchone()[0]
    
    # Finish
    con.close()
    with open("completed_scans.txt","a") as scans_file:
        scans_file.write('{date}\tPrices added: {scansize}\tDatabase now contains: {nr_items} items, {nr_prices} prices\n'.format(date = get_date(current_scantime), scansize = len(sql_params), nr_items = nr_items, nr_prices = nr_prices))
    return True
    
if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('import.cfg')
    auctionator_path = Path(config['DEFAULT']['auctionator_path'])
    auctioneer_path = Path(config['DEFAULT']['auctioneer_path'])
    if not auctionator_path or not auctioneer_path:
        print ('Fill out auc path into import.cfg')
        sys.exit(1)
    main(auctionator_path)
    