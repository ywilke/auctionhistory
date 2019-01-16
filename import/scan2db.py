import os
import sys
import re
import datetime
import sqlite3 as sqlite
import configparser
from pathlib import Path  # Don't remove
import pickle

cfg = configparser.ConfigParser()
cfg.read('import.cfg')

SERVER_LIST = pickle.load(open('../SERVER_LIST.p', 'rb'))
EXPANSIONS = pickle.load(open('../EXPANSIONS.p', 'rb'))

# Functions
def get_date(unix_time):
    '''Convert unix time to ISO 8601 date'''
    return datetime.datetime.fromtimestamp(int(unix_time)).strftime('%Y-%m-%d %H:%M:%S')


def write_debug(message):
    '''Write a message to the debug log'''
    with open('debug.log','a') as debug_f:
        stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        debug_f.write(f"{stamp} {message}\n")


def quit_script(message, con):
    '''Rollback and close database then exit script'''
    con.rollback()
    con.close()
    write_debug(f'FATAL ERROR: {message}')
    sys.exit(1)


def check_scantime(server, con, cur):
    '''Return time of scan but returns False if it was not a new scan'''
    min_diff = 1800
    cur.execute("SELECT MAX(scantime) FROM scans;")
    current_scantime = 0
    last_scantime = cur.fetchone()[0]
    if not last_scantime:
        last_scantime = 0  
    if server['scan'] == 'auctionator_wotlk':
        if not os.path.exists(server['savedvar'] / 'Auctionator.lua'):
            return False
        with open(server['savedvar'] / 'Auctionator.lua', 'r') as import_file:
            for line in import_file:
                if line.split(' ')[0] == 'AUCTIONATOR_LAST_SCAN_TIME': # Gets the time of last scan
                    current_scantime = int(line.split(' ')[2])
                    if current_scantime - last_scantime <= min_diff: 
                        return False
                    else:
                        return current_scantime
    
    elif server['scan'] == 'auctioneer_tbc' or server['scan'] == 'auctioneer_wotlk':
        scantimes = []
        if not os.path.exists(server['savedvar'] / 'Auc-ScanData.lua'):
            return False
        with open(server['savedvar'] / 'Auc-ScanData.lua', 'r') as import_file:
            for line in import_file:
                if line.split(' ', 1)[0] == '\t\t\t\t\t\t["startTime"]':
                    find = re.search('(\d+),', line.split(' ')[2])
                    scantimes.append(int(find.group(1)))
            try:
                current_scantime = min(scantimes)
            except ValueError:
                return False
            if current_scantime - last_scantime <= min_diff: 
                return False
            else:
                return current_scantime

    elif server['scan'] == 'auctioneer_clas':
        if not os.path.exists(server['savedvar'] / 'Auctioneer.lua'):
            return False
        with open(server['savedvar'] / 'Auctioneer.lua', 'r') as import_file:
            for line in import_file:
                if line.split(' ', 1)[0] == 'scantime':
                    current_scantime = int(line.split(' ')[2])
                    break
            if current_scantime - last_scantime <= min_diff: 
                return False
            else:
                return current_scantime


def parse_scandata(server):
    '''Extract items and their price from scandata'''
    if server['scan'] == 'auctionator_wotlk':
        with open(server['savedvar'] / 'Auctionator.lua', 'r') as import_file:
            importing = False
            data = {}
            pattern = '\t\["('
            first = True
            for i in server['realms']:
                if first == True:
                    pattern += f"{i['realm']}_Alliance|{i['realm']}_Horde"
                    first = False
                else:
                    pattern += f"|{i['realm']}_Alliance|{i['realm']}_Horde"
            pattern += ')"\] = {'
            for line in import_file:
                line = line.rstrip()
                if importing == False:
                    servermatch = re.match(pattern, line)
                    if servermatch:
                        realm = servermatch.group(1)
                        for realm_obj in server['realms']:  # Reformat realm name
                            if realm_obj['name'] in realm:
                                realm = realm.replace(realm_obj['realm'], realm_obj['name'])
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
    
    elif server['scan'] == 'auctioneer_tbc' or server['scan'] == 'auctioneer_wotlk':
        first = True
        low_price = {}
        for i in server['realms']:
            low_price[f"{i['name']}_Alliance"] = {}
            low_price[f"{i['name']}_Horde"] = {}
        
        pattern = '\t\t\["('
        for i in server['realms']:
            if first == True:
                pattern += f"{i['realm']}"
                first = False
            else:
                pattern += f"|{i['realm']}"
        pattern += ')"\] = {'
        with open(server['savedvar'] / 'Auc-ScanData.lua', 'r') as import_file:
            data = {}
            realm = None
            if server['scan'] == 'auctioneer_tbc':
                begin = '\t\t\t\t["image"]'
            elif server['scan'] == 'auctioneer_wotlk':
                begin = '\t\t\t\t\t"return'
            for line in import_file:
                line = line.rstrip()
                realmmatch = re.match(pattern, line) # Set current realm
                if realmmatch:
                    raw_realm = realmmatch.group(1)
                    for realm_obj in server['realms']:  # Reformat realm name
                        if realm_obj['name'] in raw_realm:
                            raw_realm = raw_realm.replace(realm_obj['realm'], realm_obj['name'])
                    continue
                factionmatch = re.match('\t\t\t\["(Alliance|Horde)"\] = {', line)
                if factionmatch:
                    realm = raw_realm + f"_{factionmatch.group(1)}" # Add faction to realmname
                    print (realm)
                    continue
                if line.split(' ', 1)[0] == begin:
                    line = line.split('return {', 1)[1]
                    line = line.split('},')
                    for entry in line:
                        values = entry.split(',')
                        if len(values) != 28:
                            continue
                        if len(values) == 28:
                            item = re.search('h\[(.+)\]', values[0]).group(1)
                            buyout = int(values[16])
                            stack = int(values[10])
                            price = int(buyout / stack)
                            if price == 0: # Bid only, no buyout
                                continue
                            if item not in low_price[realm]:
                                low_price[realm][item] = price
                            elif price < low_price[realm][item]:
                                low_price[realm][item] = price
                                
        for realm in low_price:
            data[realm] = []
            for item in low_price[realm]:
                price = low_price[realm][item]
                data[realm].append((price, item))
        return data

    elif server['scan'] == 'auctioneer_clas':
        low_price = {}
        for i in server['realms']:
            low_price[f"{i['name']}_Alliance"] = {}
            low_price[f"{i['name']}_Horde"] = {}
        first = True
        pattern = '\t\t\["('
        for i in server['realms']:
            if first == True:
                pattern += f"{i['realm']}-Alliance|{i['realm']}-Horde"
                first = False
            else:
                pattern += f"|{i['realm']}-Alliance|{i['realm']}-Horde"
        pattern += ')"\] = {'
        with open(server['savedvar'] / 'Auctioneer.lua', 'r') as import_file:
            importing = False
            realm = None
            data = {}
            for line in import_file:
                line = line.rstrip()
                if importing == False:
                    if line == '\t["snap"] = {':
                        importing = True
                    continue

                realmmatch = re.match(pattern, line)
                if realmmatch != None:
                    realm = realmmatch.group(1).replace('-', '_')
                    realm = realm.replace(' ', '_')
                    for realm_obj in server['realms']:  # Reformat realm name
                        if realm_obj['name'] in realm:
                            realm = realm.replace(realm_obj['realm'], realm_obj['name'])
                            print(realm)
                    realmmatch = None
                    continue

                if line[0:4] == '\t\t\t\t':
                    values = (line.split('] = ', 1)[0]).split(':')
                    if len(values) == 8:
                        item = values[3]
                    elif len(values) == 9:
                        item = f"{values[3]}:{values[4]}"
                    else:
                        write_debug(f'Error: Abnormal value len:{len(values)} for {realm}. {line}')
                    buyout = int(values[len(values) - 2])
                    stack = int(values[len(values) - 4])
                    price = int(buyout / stack)
                    if price == 0: # Bid only, no buyout
                        continue
                    if item not in low_price[realm]:
                        low_price[realm][item] = price
                    elif price < low_price[realm][item]:
                        low_price[realm][item] = price

        for realm in low_price:
            data[realm] = []
            for item in low_price[realm]:
                price = low_price[realm][item]
                data[realm].append((price, item))
        return data


def main():
    # Create DB file
    if not os.path.exists("auctionhistory.db"):
        open("auctionhistory.db","w").close()
    # Connect to DB
    con = sqlite.connect('auctionhistory.db')
    cur = con.cursor()  
    # Create Tables
    with con:
        cur.execute("CREATE TABLE IF NOT EXISTS scans("
                    "scanid INTEGER PRIMARY KEY,"
                    "scantime INT UNIQUE);")
        for expan in EXPANSIONS:
            cur.execute(f'''CREATE TABLE IF NOT EXISTS {expan}_items(
                itemid INTEGER PRIMARY KEY,
                itemname TEXT UNIQUE COLLATE NOCASE);''')
        for server in SERVER_LIST:
            expan = server['expansion']
            for realm_obj in server['realms']:
                realm = realm_obj['name']
                for faction in ['A', 'H']:
                    cur.execute(f'''CREATE TABLE IF NOT EXISTS {realm}_{faction}_prices(
                                priceid INTEGER PRIMARY KEY, 
                                price INT, 
                                itemid INT, 
                                scanid INT, 
                                FOREIGN KEY(scanid) REFERENCES scans(scanid), 
                                FOREIGN KEY(itemid) REFERENCES {expan}_items(itemid));''')
                    cur.execute(f'''CREATE INDEX IF NOT EXISTS idx_{realm}_{faction}_item 
                                ON {realm}_{faction}_prices (itemid);''')

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
        sql_vars.update(parse_scandata(server))
    if scantime == False: # No valid scans
        quit_script('No valid scans(already imported?)', con)
    # Insert into DB
    cur.execute("INSERT INTO scans (scantime) VALUES (?);", (scantime,))

    for server in SERVER_LIST:
        expan = server['expansion']
        for realm_obj in server['realms']:
            realm = realm_obj['name']
            for faction in ['Alliance', 'Horde']:
                try:
                    data = sql_vars[f'{realm}_{faction}']
                except KeyError:
                    continue
                cur.executemany(f'INSERT OR IGNORE INTO {expan}_items (itemname) VALUES (?)',
                    ((i[1],)for i in data))
                short = f'{realm}_{faction[0]}'
                sql = (f'''INSERT INTO {short}_prices (price, itemid, scanid) 
                    SELECT ?, sub.itemid, sub.scanid 
                    FROM (SELECT {expan}_items.itemid, scans.scanid 
                    FROM {expan}_items, scans 
                    WHERE {expan}_items.itemname = ? 
                    AND scans.scantime = ?) sub;''')
                try: # Insert prices
                    cur.executemany(sql, ((i[0], i[1], scantime)for i in data))
                except Exception as e:
                    quit_script(f'While inserting prices for {short}: {e}', con)
    con.commit()
    # Create info report
    realm_rep = ''
    expan_rep = ''
    scan_price = 0
    expan_prices = {}
    
    cur.execute('SELECT count(scanid) FROM scans;')
    nr_scans = cur.fetchone()[0]
    
    for expan in EXPANSIONS:
        expan_prices[expan] = 0
        
    for server in SERVER_LIST:
        expan = server['expansion']
        for realm_obj in server['realms']:
            realm = realm_obj['name']
            for faction in ['Alliance', 'Horde']:
                total_price = 0
                short = f'{realm}_{faction[0]}'
                cur.execute(f'SELECT count(price) FROM {short}_prices;')
                total_price = cur.fetchone()[0]
                try:
                    nr_prices = len(sql_vars[f'{realm}_{faction}'])
                except KeyError:
                    nr_prices = 0
                scan_price += nr_prices
                realm_rep += f' {short}: {nr_prices}'
                expan_prices[expan] += total_price

    for expan in EXPANSIONS:
        cur.execute(f'SELECT count(itemid) FROM {expan}_items;')
        nr_items = cur.fetchone()[0]
        expan_rep += f' {expan.upper()}: {nr_items}items {expan_prices[expan]}prices'
    
    date = get_date(scantime)
    with open("completed_scans.txt","a") as report_f:
        report_f.write(f"{date}\tPrices added: {scan_price}\t{expan_rep}\t{nr_scans} scans\t{realm_rep}\n")
    con.close()
    return


if __name__ == "__main__":
    main()
