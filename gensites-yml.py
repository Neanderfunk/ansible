#!/usr/bin/env python3

import yaml
import hashlib
import ipaddr
import jinja2
import os
   
def getMacFromString(string):
    stringHash = hashlib.sha1(string.encode()).hexdigest()
    return \
    stringHash[0] + '0:' + stringHash[2:4] + ':' + stringHash[4:6] \
    + ':' + stringHash[8:10] + ':' + stringHash[12:14] + ':' + stringHash[16:18]

sitesInHandle=open('vars/sites.yml.in', 'r')

sites=yaml.load(sitesInHandle)

for node in range(len(sites['supernodes'])):
  sites['supernodes'][node]['fqdn'] = sites['supernodes'][node]['host'] + sites['supernodes'][node]['domain']

for site_code in sites['sites'].keys():
    sites['sites'][site_code]['bssid'] = getMacFromString('bssid' + site_code)
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
        supernodes[ver]=list((sn['host'], next(hostaddr)) for sn in sites['supernodes'])

        sites['sites'][site_code]['supernodeAddr' + ver] = \
            dict((node[0], str(node[1])) for node in supernodes[ver])
    
    sites['sites'][site_code]['next_node4'] = str(supernodes['4'][0][1] + 254)
    sites['sites'][site_code]['next_node6'] = str(supernodes['6'][0][1] + 0xfffe)

    sites['sites'][site_code]['dhcp'] = {'range': {}}
    currentIP=supernodes['4'][0][1] + sites['sites'][site_code]['reserved_ip_addresses']
    for sn in sites['supernodes']:
      sites['sites'][site_code]['dhcp']['range'][sn['host']] = {'from': str(currentIP) }
      currentIP += int((ip['4'].numhosts - sites['sites'][site_code]['reserved_ip_addresses'] - 2) / len(sites['supernodes']))
      sites['sites'][site_code]['dhcp']['range'][sn['host']]['to'] = str(currentIP-1)

    sites['sites'][site_code]['bridge'] = 'br0' if site_code == 'ffnef-met' else 'br-' + site_code.split('-')[-1]

    sites['sites'][site_code]['fastd'] = {
            'peers': sites['sites'][site_code]['fastd'],
            'limit': 200,
            'mtu': 1364,
            'interface': 'bat-' + site_code.split('-')[-1],
            'mac': dict((node[0], getMacFromString('fastd'+site_code+node[0])) for node in supernodes[ver])
            }
    sites['sites'][site_code]['batman'] = {
            'mac': dict((node[0], getMacFromString('batman'+site_code+node[0])) for node in supernodes[ver]),
            'interface': 'tap-' + site_code.split('-')[-1]
            }
   
    fastd_template = jinja2.Template("""key "{{ key }}";
remote ipv4 "{{ host }}" port {{ port }};

""");
    i=0
    try:
      os.mkdir ('out/fastd-peers/')
    except FileExistsError:
      True

    for peer in sites['sites'][site_code]['fastd']['peers']:
        try:
            os.mkdir ('out/fastd-peers/' + site_code[2:])
        except FileExistsError:
          True

        peerFile = open('out/fastd-peers/' + site_code[2:] + '/' +
            site_code.split('-')[1] + str(i), 'w')
        peerFile.write (fastd_template.render(host=peer,
            key=sites['sites'][site_code]['fastd']['peers'][peer]['key'],
            port=sites['sites'][site_code]['fastd']['peers'][peer]['port']))
        peerFile.close()
        i = i+1

        

#print (yaml.dump(sites, default_flow_style=False))
sitesOutHandle=open('vars/sites.yml', 'w')
sitesOutHandle.write (yaml.dump(sites, default_flow_style=False))
sitesOutHandle.close()
