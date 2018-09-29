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

cfg = configparser.ConfigParser()
cfg.read('import.cfg')

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
    

# Functions
def get_date(unix_time):# Converts unix time to ISO 8601 date.
    return datetime.datetime.fromtimestamp(int(unix_time)).strftime('%Y-%m-%d %H:%M:%S')


def write_debug(message):
    with open('debug.log','a') as debug_f:
        time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        debug_f.write(f"{time} {message}\n")


def quit_script(message, con):
    con.rollback()
    con.close()
    write_debug(message)
    time.sleep(5)
    sys.exit(1)


def check_scantime(server, con, cur):
    auctionator_path = server['auctionator']
    with open(auctionator_path / 'Auctionator.lua', 'r') as import_file:
        for line in import_file:
            if line.split(' ')[0] == 'AUCTIONATOR_LAST_SCAN_TIME': # Gets the time of last scan
                current_scantime = int(line.split(' ')[2])
                cur.execute("SELECT MAX(scantime) FROM WOTLK_scans;")
                last_scantime = cur.fetchone()[0]
                if not last_scantime:
                    last_scantime = 0 
                if current_scantime - last_scantime <= 7200: 
                    return False
                else:
                    return current_scantime


def parse_auctionator(server):
    auctionator_path = server['auctionator']
    with open(auctionator_path / 'Auctionator.lua', 'r') as import_file:
        importing = False
        data = {}
        pattern = '\t\["('
        first = True
        for i in server['realms']:
            if first == True:
                pattern += f"{i['realm']}_Alliance|{i['realm']}_Horde"
                first = False
            pattern += f"|{i['realm']}_Alliance|{i['realm']}_Horde"
        pattern += ')"\] = {'
        for line in import_file:
            line = line.rstrip()
            if importing == False:
                servermatch = re.match(pattern, line)
                if servermatch:
                    realm = servermatch.group(1)
                    realm = realm.replace(' 1x','')
                    print (realm)
                    data[realm] = []
                    importing = True # Starts import at first item
                continue
            if line == "	},": # End of pricelist
                realm = None
                importing = False
                continue
            itemmatch = re.match('\t\t\[\"(.+)\] = (\d+),', line)
            item = itemmatch.group(1)[:-1]
            price = int(itemmatch.group(2))
            data[realm].append((price, item))
    return data

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


def main():
    # Create DB file
    if not os.path.exists("auctionhistory.db"):
        open("auctionhistory.db","w").close()
    
    # Connect to DB
    con = sqlite.connect('auctionhistory.db')
    cur = con.cursor()  
    
    # Create Tables
    with con:    
        cur.execute("CREATE TABLE IF NOT EXISTS WOTLK_items("
                    "itemid INTEGER PRIMARY KEY,"
                    "itemname TEXT UNIQUE COLLATE NOCASE);")
            
        cur.execute("CREATE TABLE IF NOT EXISTS WOTLK_scans("
                    "scanid INTEGER PRIMARY KEY,"
                    "scantime INT UNIQUE);")

        cur.execute("CREATE TABLE IF NOT EXISTS Lordaeron_A_prices("
                    "priceid INTEGER PRIMARY KEY,"
                    "price INT,"
                    "itemid INT,"
                    "scanid INT,"
                    "FOREIGN KEY(scanid) REFERENCES WOTLK_scans(scanid),"
                    "FOREIGN KEY(itemid) REFERENCES WOTLK_items(itemid));")

        cur.execute("CREATE TABLE IF NOT EXISTS Lordaeron_H_prices("
                    "priceid INTEGER PRIMARY KEY,"
                    "price INT,"
                    "itemid INT,"
                    "scanid INT,"
                    "FOREIGN KEY(scanid) REFERENCES WOTLK_scans(scanid),"
                    "FOREIGN KEY(itemid) REFERENCES WOTLK_items(itemid));")

        cur.execute("CREATE TABLE IF NOT EXISTS Icecrown_A_prices("
                    "priceid INTEGER PRIMARY KEY,"
                    "price INT,"
                    "itemid INT,"
                    "scanid INT,"
                    "FOREIGN KEY(scanid) REFERENCES WOTLK_scans(scanid),"
                    "FOREIGN KEY(itemid) REFERENCES WOTLK_items(itemid));")
        
        cur.execute("CREATE TABLE IF NOT EXISTS Icecrown_H_prices("
                    "priceid INTEGER PRIMARY KEY,"
                    "price INT,"
                    "itemid INT,"
                    "scanid INT,"
                    "FOREIGN KEY(scanid) REFERENCES WOTLK_scans(scanid),"
                    "FOREIGN KEY(itemid) REFERENCES WOTLK_items(itemid));")

        cur.execute("CREATE TABLE IF NOT EXISTS Echoes_A_prices("
                    "priceid INTEGER PRIMARY KEY,"
                    "price INT,"
                    "itemid INT,"
                    "scanid INT,"
                    "FOREIGN KEY(scanid) REFERENCES WOTLK_scans(scanid),"
                    "FOREIGN KEY(itemid) REFERENCES WOTLK_items(itemid));")
        
        cur.execute("CREATE TABLE IF NOT EXISTS Echoes_H_prices("
                    "priceid INTEGER PRIMARY KEY,"
                    "price INT,"
                    "itemid INT,"
                    "scanid INT,"
                    "FOREIGN KEY(scanid) REFERENCES WOTLK_scans(scanid),"
                    "FOREIGN KEY(itemid) REFERENCES WOTLK_items(itemid));")
        
        cur.execute("CREATE INDEX IF NOT EXISTS idx_Lordaeron_A_item ON Lordaeron_A_prices (itemid);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_Lordaeron_H_item ON Lordaeron_H_prices (itemid);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_Icecrown_A_item ON Icecrown_A_prices (itemid);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_Icecrown_H_item ON Icecrown_H_prices (itemid);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_Echoes_A_item ON Echoes_A_prices (itemid);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_Echoes_H_item ON Echoes_H_prices (itemid);")

    # Importing
    scantime = False
    sql_vars = {}
    for server in SERVER_LIST:
        time_check = check_scantime(server, con, cur)
        if time_check == False: # Scan did not happen or it was a old scan
            write_debug(f"No valid scan found for {server['server']}")
            continue # Move on to next sever
        if time_check > scantime: # Latest scantime will be written in db
            scantime = time_check
        # parse file
        sql_vars.update(parse_auctionator(server))
    if scantime == False: # No valid scans
        quit_script('No valid scans(already imported)', con)
    scantime = scantime + random.randint(-1800,1800)
    # Insert into DB
    cur.execute("INSERT INTO WOTLK_scans (scantime) VALUES (?);",
        (scantime,))

    for rf in sql_vars: # rf = specific realm & faction combi
        data = sql_vars[rf]
        cur.executemany('INSERT OR IGNORE INTO WOTLK_items (itemname) VALUES (?)',
            ((i[1],)for i in data))
        rf_match = re.match('((.+?_(A|H))).+', rf)
        short = rf_match.group(1)
        sql = (f"INSERT INTO {short}_prices (price, itemid, scanid) "
            "SELECT ?, sub.itemid, sub.scanid "
            "FROM (SELECT WOTLK_items.itemid, WOTLK_scans.scanid "
            "FROM WOTLK_items, WOTLK_scans "
            "WHERE WOTLK_items.itemname = ? "
            "AND WOTLK_scans.scantime = ?) sub;")
        try: # Insert prices
            cur.executemany(sql, ((i[0], i[1], scantime)for i in data))
        except Exception as e:
            print(e)
            con.rollback()
            con.close()
            sys.exit(1)
    con.commit()
    # Create info report
    report = ''
    total_price = 0
    scan_price = 0
    
    for rf in sql_vars:
        nr_prices = len(sql_vars[rf])
        scan_price += nr_prices
        report += f" {rf}: {nr_prices}"
        rf_match = re.match('((.+?_(A|H))).+', rf)
        short = rf_match.group(1)
        cur.execute(f'SELECT count(price) FROM {short}_prices;')
        total_price += cur.fetchone()[0]
    cur.execute('SELECT count(itemid) FROM WOTLK_items;')
    nr_items = cur.fetchone()[0]
    cur.execute('SELECT count(scanid) FROM WOTLK_scans;')
    nr_scans = cur.fetchone()[0]
    con.close()
    date = get_date(scantime)
    with open("completed_scans.txt","a") as report_f:
        report_f.write(f"{date}\tPrices added: {scan_price}\tDB contains: {nr_items} items, {total_price} prices, {nr_scans} scans\t{report}\n")
    return


if __name__ == "__main__":
    main()

'''
    # Auctioneer TBC import (disabled: 0 prices)            
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