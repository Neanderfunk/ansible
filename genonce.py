#!/usr/bin/env python3

import yaml
import hashlib
   
def getMacFromString(string):
    return \
	string[:2] + ':' + string[2:4] + ':' + string[4:6] \
	+ ':' + string[8:10] + ':' + string[12:14] + ':' + string[16:18]

sitesInHandle=open('files/sites.yml.in', 'r')

sites=yaml.load(sitesInHandle)
for site_code in sites['sites'].keys():
    site_hash = hashlib.sha1(site_code.encode()).hexdigest()
    sites['sites'][site_code]['bssid'] = getMacFromString('bssid' + site_hash)
    sites['sites'][site_code]['next_mac'] = getMacFromString('next_mac' + site_hash)

#print (yaml.dump(sites, default_flow_style=False))
sitesOutHandle=open('files/sites.yml', 'w')
sitesOutHandle.write (yaml.dump(sites, default_flow_style=False))
sitesOutHandle.close()
