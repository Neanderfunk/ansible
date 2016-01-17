#!/usr/bin/python3

import enum
import ipaddress
import yaml

class PartOfMail(enum.Enum):
	text=0
	gettingEndpoints=1
	waitingForTunnels=2
	gettingTunnels=3

greMail=open('files/gre-mail', 'r')
greRouters={}
mode=PartOfMail.text
curRouter=''
curSupernode=''
curTunnel={}

for line in greMail:
	line=line.strip()
	if line.find('Endpunkte') != -1:
		mode=PartOfMail.gettingEndpoints
	elif mode == PartOfMail.gettingEndpoints:
		if line != "":
			try:
				(host, ip)=line.split(' ')
				greRouters[host]={
					'ip': str(ipaddress.ip_address(ip)),
					'tunnels': []}
			except ValueError:
				mode = PartOfMail.waitingForTunnels
			except TypeError:
				mode = PartOfMail.waitingForTunnels
	elif mode == PartOfMail.waitingForTunnels:
		parts = line.split(' ')
		if len(parts) == 4:
			router, nul, supernode, ip = parts
			
			possibleMatch=True
			if not router in greRouters:
				possibleMatch=False
			if possibleMatch:
				ip = ipaddress.ip_address(ip[1:-1]) # can die
				mode = PartOfMail.gettingTunnels

	if mode == PartOfMail.gettingTunnels:
		if line.find('-') != -1:
			curRouter, nul, curSupernode, supernodeIp = line.split(' ')
			greRouters[curRouter]['tunnels'].append({
				'supernode': curSupernode,
				"localIp4": supernodeIp[1:-1] })
		elif line.find('/') != -1:
			ip, netmask = line.split('/')
			ip = ipaddress.ip_address(ip) # can die
			ipPair = { 'local': str(ip+1), 'remote': str(ip) }
			if type(ip) == ipaddress.IPv4Address:
				greRouters[curRouter]['tunnels'][-1]['ip4']=ipPair
			elif type(ip) == ipaddress.IPv6Address:
				greRouters[curRouter]['tunnels'][-1]['ip6']=ipPair
		else:
			break

#print (greRouters)
#print (yaml.dump(greRouters, default_flow_style=False))

greTunnels={}

for router in greRouters:
	for supernode in greRouters[router]['tunnels']:
		if not (supernode['supernode'] in greTunnels):
			greTunnels[supernode['supernode']]={}
			
		greTunnels[supernode['supernode']][router]=supernode
		greTunnels[supernode['supernode']][router]['endpoint']=greRouters[router]['ip']
		greTunnels[supernode['supernode']][router].pop('supernode')

#print (yaml.dump(greTunnels, default_flow_style=False))
greTunnelsHandle=open('vars/greTunnels.yml', 'w')
greTunnelsHandle.write (yaml.dump({'greTunnels': greTunnels}, default_flow_style=False))
greTunnelsHandle.close()
