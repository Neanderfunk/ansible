#!/usr/bin/env python3

import yaml
import hashlib
   
def getMacFromString(string):
    stringHash = hashlib.sha1(string.encode()).hexdigest()
    return \
	stringHash[0] + '0:' + stringHash[2:4] + ':' + stringHash[4:6] \
	+ ':' + stringHash[8:10] + ':' + stringHash[12:14] + ':' + stringHash[16:18]

sitesInHandle=open('files/sites.yml.in', 'r')

sites=yaml.load(sitesInHandle)
for site_code in sites['sites'].keys():
    sites['sites'][site_code]['bssid'] = getMacFromString('bssid' + site_code)
    sites['sites'][site_code]['next_mac'] = getMacFromString('next_mac' + site_code)
    sites['sites'][site_code]['site_name'] = 'Freifunk ' + sites['sites'][site_code]['site']

#print (yaml.dump(sites, default_flow_style=False))
sitesOutHandle=open('files/sites.yml', 'w')
sitesOutHandle.write (yaml.dump(sites, default_flow_style=False))
sitesOutHandle.close()
