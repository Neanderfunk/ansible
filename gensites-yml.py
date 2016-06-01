#!/usr/bin/env python3

import yaml
import hashlib
import ipaddr
import jinja2
import os
import json
   
def getMacFromString(string):
    stringHash = hashlib.sha1(string.encode()).hexdigest()
    return \
    stringHash[0] + '0:' + stringHash[2:4] + ':' + stringHash[4:6] \
    + ':' + stringHash[8:10] + ':' + stringHash[12:14] + ':' + stringHash[16:18]

def mac2IPv6linklocal(mac):
    # Remove the most common delimiters; dots, dashes, etc.
    mac_value = int(mac.replace(':', ''), 16)
    #
    # Split out the bytes that slot into the IPv6 address
    # XOR the most significant byte with 0x02, inverting the 
    # Universal / Local bit
    high2 = mac_value >> 32 & 0xffff ^ 0x0200
    high1 = mac_value >> 24 & 0xff
    low1 = mac_value >> 16 & 0xff
    low2 = mac_value & 0xffff
    #
    return 'fe80::{:04x}:{:02x}ff:fe{:02x}:{:04x}'.format(high2, high1, low1, low2)

sitesInHandle=open('vars/sites.yml.in', 'r')

sites=yaml.load(sitesInHandle)

sites['is_supernode'] = {}
sites['supernodesByName'] = {}
sites['own_sites'] = {}

for node in range(len(sites['supernodes'])):
  hostname = sites['supernodes'][node]['host']
  sites['supernodes'][node]['fqdn'] = hostname + '.' + sites['supernodes'][node]['domain']
  sites['is_supernode'][hostname] = True

  sites['supernodesByName'][hostname] = sites['supernodes'][node]

for site_code in sites['sites'].keys():
    foreign = True
    if site_code.find('-') >= 0:
        if site_code.split('-')[0] == sites['config']['my_meta_community']:
            foreign = False
    
    sites['sites'][site_code]['foreign'] = foreign

    sites['sites'][site_code]['bssid'] = getMacFromString('bssid' + site_code)
    if not foreign:
        sites['sites'][site_code]['next_mac'] = getMacFromString('next_mac' + site_code)
        sites['sites'][site_code]['site_name'] = 'Freifunk ' + sites['sites'][site_code]['site']

    ip = {
        '4': ipaddr.IPNetwork(sites['sites'][site_code]['compressed4']),
        '6': ipaddr.IPNetwork(sites['sites'][site_code]['compressed6'])
    }

    supernodes={}
    
    assert(ip['6'].prefixlen <= 64);
    assert(ip['4'].prefixlen <= 22);

    for ver in ip:
        sites['sites'][site_code]['network' + ver] = str(ip[ver].network)
        sites['sites'][site_code]['prefixlen' + ver] = ip[ver].prefixlen
        sites['sites'][site_code]['netmask' + ver] = str(ip[ver].netmask)

        hostaddr=ip[ver].iterhosts()

        if not foreign:
            supernodes[ver]=list((sn['host'], next(hostaddr)) for sn in sites['supernodes'])
    
            sites['sites'][site_code]['supernodeAddr' + ver] = \
                dict((node[0], str(node[1])) for node in supernodes[ver])
       
    if not foreign:
        sites['sites'][site_code]['next_node4'] = str(supernodes['4'][0][1] + 254)
        sites['sites'][site_code]['next_node6'] = str(supernodes['6'][0][1] + 0xfffe)
        
        sites['sites'][site_code]['extra_networks6'] = list(str(ip['6'].network+(n*16**18))+'/64' for n in range(sites['config']['konzentratoren']))
    
        sites['sites'][site_code]['dhcp'] = {'range': {}}
        currentIP=supernodes['4'][0][1] + sites['sites'][site_code]['reserved_ip_addresses']
    for sn in sites['supernodes']:
        if not foreign:
          sites['sites'][site_code]['dhcp']['range'][sn['host']] = {'from': str(currentIP) }
          currentIP += int((ip['4'].numhosts - sites['sites'][site_code]['reserved_ip_addresses'] - 2) / len(sites['supernodes']))
          sites['sites'][site_code]['dhcp']['range'][sn['host']]['to'] = str(currentIP-1)

    sites['sites'][site_code]['bridge'] = 'br0' if site_code == 'ffnef-met' else 'br-' + site_code.split('-')[-1]

    sites['sites'][site_code]['fastd'] = {
        'peers': sites['sites'][site_code]['fastd'],
        'limit': 200,
        'mtu': 1364,
        'interface': 'tap-' + site_code.split('-')[-1],
        'mac': (False if foreign else dict((node[0],
            getMacFromString('fastd'+site_code+node[0])) for node in supernodes[ver]))
        }
    sites['sites'][site_code]['batman'] = {
            'mac': (False if foreign else dict((node[0],
        getMacFromString('batman'+site_code+node[0])) for node in supernodes[ver])),
            'interface': 'bat-' + site_code.split('-')[-1]
            }
   
    fastd_template = jinja2.Template("""key "{{ key }}";
remote ipv4 "{{ host }}" port {{ port }};

""");
    i=0
    try:
      os.mkdir ('out/fastd-peers/')
    except Exception:
      True

    if not foreign:
        sites['own_sites'][site_code] = sites['sites'][site_code]
    
        for peer in sites['sites'][site_code]['fastd']['peers']:
            try:
                os.mkdir ('out/fastd-peers/' + site_code[2:])
            except Exception:
              True
    
            if site_code.find('-') >= 0:
                peerFile = open('out/fastd-peers/' + site_code[2:] + '/' +
                    site_code.split('-')[1] + str(i), 'w')
                peerFile.write (fastd_template.render(host=peer,
                    key=sites['sites'][site_code]['fastd']['peers'][peer]['key'],
                    port=sites['sites'][site_code]['fastd']['peers'][peer]['port']))
                peerFile.close()
                i = i+1

sites['site_partitions'] = { 'all': sites['sites'], 'own': sites['own_sites'] }
        

#print (yaml.dump(sites, default_flow_style=False))
sitesOutHandle=open('vars/sites.yml', 'w')
sitesOutHandle.write (yaml.dump(sites, default_flow_style=False))
sitesOutHandle.close()

for site_code in sites['own_sites']:
	aliases={}
	for node in sites['sites'][site_code]['fastd']['mac']:
		if 'installed' in sites['supernodesByName'][node].keys():
			mac = sites['sites'][site_code]['fastd']['mac'][node]
			batmanMac = sites['sites'][site_code]['batman']['mac'][node]
			compactMac = mac.replace(':', '')
			aliases[compactMac] = {
	"firstseen": sites['supernodesByName'][node]['installed'],
    "nodeinfo": {
      "owner": {
        "contact": "admin@neanderfunk.de"
      },
      "node_id": compactMac,
      "network": {
        "mac": mac,
        "mesh_interfaces": [
          mac,
          batmanMac,
        ],
        "addresses": [
         sites['sites'][site_code]['supernodeAddr4'][node],
         sites['sites'][site_code]['supernodeAddr6'][node],
		 mac2IPv6linklocal(mac),
        ],
        "mesh": {
          sites['sites'][site_code]['fastd']['interface']: {
            "interfaces": {
              "tunnel": [
                batmanMac,
              ],
              "other": [
                mac,
              ]
            }
          }
        }
      },
      "hostname": node + ".ffnef.de",
      "hardware": {
        "model": "esxi",
        "nproc": 2
      },
      "software": {
        "batman-adv": {
          "compat": 15,
          "version": "2015.1"
        },
        "fastd": {
          "enabled": True
        },
        "autoupdater": {
          "enabled": True,
        },
        "firmware": {
          "base": "Ubuntu",
          "release": "15.10"
        }
      },
      "system": {
        "site_code": site_code
      }
	}
	}
	aliasesOutHandle=open('out/aliases.json/aliases.json.' + site_code.replace('ffnef-', 'nef'), 'w')
	aliasesOutHandle.write(json.dumps(aliases, indent=2))
	aliasesOutHandle.close()
