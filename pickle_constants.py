import pickle
from pathlib import Path
import configparser

cfg = configparser.ConfigParser()
cfg.read('import/import.cfg')

SERVER_LIST = [
    {
        "server": 'warmane',
        "expansion": 'wotlk',
        "scan": 'auctionator_wotlk',
        "realmlist": 'logon.warmane.com',
        "realms": [
            {
                "realm": 'Lordaeron',
                "name": 'Lordaeron',
                "auc_pos_A": (1009, 441),
                "auc_pos_H": (958, 311),
            },
            {
                "realm": 'Icecrown',
                "name": 'Icecrown',
                "auc_pos_A": (1009, 251),
                "auc_pos_H": (966, 326),
            }
        ],
        "user": cfg['warmane']['user'],
        "pass": cfg['warmane']['pass'],
        "savedvar": Path(cfg['warmane']['savedvar_wotlk']),
    },
    {
        "server": 'gamerdistrict',
        "expansion": 'wotlk',
        "scan": 'auctionator_wotlk', 
        "realmlist": 'wotlk.gamer-district.org',
        "realms": [
            {
                "realm": 'Echoes 1x',
                "name": 'Echoes',
                "auc_pos_A": (930, 446),
                "auc_pos_H": (983, 274),
            }
        ],
        "user": cfg['gamerdistrict']['user'],
        "pass": cfg['gamerdistrict']['pass'],
        "savedvar": Path(cfg['gamerdistrict']['savedvar_wotlk']),
    },
    {
        "server": 'sunwell',
        "expansion": 'wotlk',
        "scan": 'auctioneer_wotlk',
        "realmlist": 'logon.sunwell.pl',
        "realms": [
            {
                "realm": 'Angrathar',
                "name": 'Angrathar',
                "auc_pos_A": (919, 462),
                "auc_pos_H": (798, 339),
            }
        ],
        "user": cfg['sunwell']['user'],
        "pass": cfg['sunwell']['pass'],
        "savedvar": Path(cfg['sunwell']['savedvar_wotlk']),
    },
    {
        "server": 'dalaran-wow',
        "expansion": 'wotlk',
        "scan": 'auctioneer_wotlk',
        "realmlist": 'logon.dalaran-realmlist.org',
        "realms": [
            {
                "realm": 'Algalon - Main Realm',
                "name": 'Algalon',
                "auc_pos_A": (870, 501),
                "auc_pos_H": (944, 311),
            }
        ],
        "user": cfg['dalaran-wow']['user'],
        "pass": cfg['dalaran-wow']['pass'],
        "savedvar": Path(cfg['dalaran-wow']['savedvar_wotlk']),
    },
    {
        "server": 'warmane',
        "expansion": 'tbc',
        "scan": 'auctioneer_tbc',
        "realmlist": 'logon.warmane.com',
        "realms": [
            {
                "realm": 'Outland',
                "name": 'Outland',
                "auc_pos_A": (965, 345),
                "auc_pos_H": (925, 288),
            }
        ],
        "user": cfg['warmane']['user'],
        "pass": cfg['warmane']['pass'],
        "savedvar": Path(cfg['warmane']['savedvar_tbc']),
    },
    {
        "server": 'sunwell',
        "expansion": 'tbc',
        "scan": 'auctioneer_tbc',
        "realmlist": 'logon.sunwell.pl',
        "realms": [
            {
                "realm": 'Nightbane',
                "name": 'Nightbane',
                "auc_pos_A": (1296, 553),
                "auc_pos_H": (1278, 511),
            }
        ],
        "user": cfg['sunwell']['user'],
        "pass": cfg['sunwell']['pass'],
        "savedvar": Path(cfg['sunwell']['savedvar_tbc']),
    },
    {
        "server": 'lights_hope',
        "expansion": 'clas',
        "scan": 'auctioneer_clas',
        "realmlist": 'logon.lightshope.org',
        "realms": [
            {
                "realm": 'Northdale',
                "name": 'Northdale',
                "auc_pos_A": (1008, 446),
                "auc_pos_H": (881, 310),
            }
        ],
        "user": cfg['lights_hope']['user'],
        "pass": cfg['lights_hope']['pass'],
        "savedvar": Path(cfg['lights_hope']['savedvar_clas']),
    },
    {
        "server": 'kronos',
        "expansion": 'clas',
        "scan": 'auctioneer_clas',
        "realmlist": 'login.kronos-wow.com',
        "realms": [
            {
                "realm": 'Kronos III',
                "name": 'Kronos_III',
                "auc_pos_A": (1391, 535),
                "auc_pos_H": (684, 476),
            }
        ],
        "user": cfg['kronos']['user'],
        "pass": cfg['kronos']['pass'],
        "savedvar": Path(cfg['kronos']['savedvar_clas']),
    },
]
pickle.dump(SERVER_LIST, open('SERVER_LIST.p', 'wb'))

EXP = {
    "clas": {
        "path": Path(cfg['DEFAULT']['clas_path']),
        "realm_path": Path(''),
        "cfg_path": Path('WTF'),
        "user": (943, 565),
        "change_realm": (1734, 72),
        "char_A": (1687, 146), # char1
        "char_H": (1657, 228), # char2
        "auctioneer": (286, 668),
        "quit": (1812, 1010),
        "ss_game": {
            "image": 'clas_game',
            "tries": 10,
            "task": 'match',
            "box": (138, 73, 203, 120),
        },
        "ss_home": {
            "image": 'clas_home',
            "tries": 10,
            "task": 'match',
            "box": (930, 1045, 933, 1048),
        },
        "ss_spawn": {
            "image": 'clas_spawn',
            "tries": 15,
            "task": 'match',
            "box": (1351, 1042, 1373, 1065),
        },
        "ss_auctioneer": {
            "image": None,
            "tries": 900,
            "task": 'diff',
            "box": (460, 279, 794, 300),
        },
    },
    "tbc": {
        "path": Path(cfg['DEFAULT']['tbc_path']),
        "realm_path": Path(''),
        "cfg_path": Path('WTF'),
        "user": (943, 565),
        "change_realm": (1734, 72),
        "char_A": (1687, 146), # char1
        "char_H": (1657, 228), # char2
        "auctioneer": (299, 168),
        "quit": (1812, 1010),
        "ss_game": {
            "image": 'tbc_game',
            "tries": 10,
            "task": 'match',
            "box": (138, 73, 203, 120),
        },
        "ss_home": {
            "image": 'tbc_home',
            "tries": 10,
            "task": 'match',
            "box": (930, 1045, 933, 1048),
        },
        "ss_spawn": {
            "image": 'tbc_spawn',
            "tries": 15,
            "task": 'match',
            "box": (1350, 1039, 1375, 1068),
        },
        "ss_auctioneer": {
            "image": None,
            "tries": 600,
            "task": 'diff',
            "box": (526, 278, 752, 320),
        },
    },
    "wotlk": {
        "path": Path(cfg['DEFAULT']['wotlk_path']),
        "realm_path": Path('Data', 'enUS'),
        "cfg_path": Path('WTF'),
        "user": (943, 565),
        "change_realm": (1734, 72),
        "char_A": (1687, 146), # char1
        "char_H": (1657, 228), # char2
        "auctionator": (712, 159),
        "auctionator_start": (506, 282),
        "auctioneer": (215, 127),
        "quit": (1812, 1010),
        "ss_game": {
            "image": 'wotlk_game',
            "tries": 10,
            "task": 'match',
            "box": (138, 73, 203, 120),
        },
        "ss_home": {
            "image": 'wotlk_home',
            "tries": 10,
            "task": 'match',
            "box": (930, 1045, 933, 1048),
        },
        "ss_auctionator": {
            "image": 'wotlk_auctionator',
            "tries": 100,
            "task": 'match',
            "box": (240, 265, 350, 290),
        },
        "ss_spawn": {
            "image": 'wotlk_spawn',
            "tries": 15,
            "task": 'match',
            "box": (1298, 1050, 1314, 1069),
        },
        "ss_auctioneer": {
            "image": None,
            "tries": 500,
            "task": 'diff',
            "box": (478, 218, 607, 254),
        },
    },

}
pickle.dump(EXP, open('EXP.p', 'wb'))
        
EXPANSIONS = []
for expan in EXP:
    EXPANSIONS.append(expan)
pickle.dump(EXPANSIONS, open('EXPANSIONS.p', 'wb'))

REALMS = {}
for server_obj in SERVER_LIST:
    server = server_obj['server']
    expan = server_obj['expansion']
    if server not in REALMS:
        REALMS[server] = {}
    for realm_obj in server_obj['realms']:
        realm = realm_obj['name']
        for faction in ['Alliance', 'Horde']:
            REALMS[server][f'{realm}_{faction}'] = expan
pickle.dump(REALMS, open('REALMS.p', 'wb'))

CAP = {"clas": 'Vanilla',
       "tbc": 'TBC',
       "wotlk": 'WotLK',
       "gamerdistrict": 'GamerDistrict',
       "warmane": 'Warmane',
       "sunwell": 'Sunwell',
       "dalaran-wow": 'Dalaran-WoW',
       "lights_hope": "Light's Hope",
       "kronos": "Kronos",
}
pickle.dump(CAP, open('CAP.p', 'wb'))