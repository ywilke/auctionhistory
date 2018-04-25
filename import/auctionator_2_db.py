# Imports
import os
import sys
import re
import datetime
import time
import sqlite3 as sqlite
import configparser
import random

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

def count_auctions(server, auctionator_path):
    with open('{}Auctionator.lua'.format(auctionator_path),'r') as auc_file:
            counting = False
            count = 0
            for line in auc_file:
                line = line.rstrip()
                
                if counting == False:
                    if line == '	["{server}"] = {{'.format(server=server):
                        counting = True # Starts count at first item
                elif counting == True:
                    if line == "	},":
                        return count
                    else:
                        count += 1

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

    # Importing
    with open('{}Auctionator.lua'.format(auctionator_path),'r') as import_file:
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
            
    with open('{}Auctionator.lua'.format(auctionator_path),'r') as import_file:
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
    auctionator_path = fix_path(config['DEFAULT']['auctionator_path'])
    if not auctionator_path:
        print ('Fill out auctionator path into import.cfg')
        sys.exit(1)
    main(auctionator_path)
    