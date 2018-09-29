import os
import configparser

def generate_import_cfg():
    if not os.path.exists("import.cfg"):
        config = configparser.ConfigParser()
        config['DEFAULT'] = {'wotlk_path': '',
                             'tbc_path': ''}

        config['warmane'] = {'auctionator': '',
                             'auctioneer': '',
                             'user': '',
                             'pass': ''}
        
        config['gamerdistrict'] = {'auctionator': '',
                                   'auctioneer': '',
                                   'user': '',
                                   'pass': ''}
       
        config['scan'] = {'prompt_timeout': '120',
                          'prompt_delay': '3600'}
        
        config['sftp'] = {'known_hosts_path': '',
                          'sftp_user': '',
                          'sftp_password': '',
                          'sftp_ip': '',
                          'sftp_dir': ''}
        
        with open('import.cfg','w') as configfile:
            config.write(configfile)
            return True

if __name__ == "__main__":
    generate_import_cfg()
        