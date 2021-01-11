#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'sifbaksh@gmail.com'

import csv
import requests
import json
import concurrent.futures
import time
import logging

logging.basicConfig(filename='dhcp_logs.log', level=logging.DEBUG)

# This will convert all Subnet Mask(i.e. 255.255.255.0) to CIDR(24) notation
def netmask_to_cidr(m_netmask):
  return(sum([ bin(int(bits)).count("1") for bits in m_netmask.split(".") ]))

# empty dictionary we are going to use the name of the space as the key
ip_space_keys = {}
auxiliaryList = []

# Start my timer
t = time.perf_counter()
'''
This first area will create all IP Space
Frist it will gather all current IP Space
We then read the entire file looking for Networks Views and then remove any dupilcates from the current list
'''
url_ip_space = "https://csp.infoblox.com/api/ddi/v1/ipam/ip_space?_fields=name,id"

headers = {
  'Authorization': 'Token YOUR_TOKEN',
  'Content-Type': 'application/json'
}
response = requests.get(url_ip_space, headers=headers)

with open('your_export.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
        if "networkcontainer" == row[0]: 
            print(row[28])
            myList = row[28]
            if myList not in auxiliaryList:
                auxiliaryList.append(myList)        
            line_count += 1
    print(f'Processed {line_count} lines.')
csv_file.close()


#auxiliaryList.remove('network_view')
#auxiliaryList.remove('')

data = json.loads(response.text)

# Remove the IP Space that are already created
for entry in data['results']:
    # add item
    ip_space_keys[entry['name']] = entry['id']
    if entry['name'] in auxiliaryList:
        print(entry['name'])
        auxiliaryList.remove(entry['name'])
payloads = []
for new_ip_space in auxiliaryList:
     payloads.append({'name':new_ip_space, 'tags':{'sif':'Yes'}})


def fetch(payload):
    create_ip_space = requests.request("post", url_ip_space , headers=headers, json = payload)
    new_space_return = json.loads(create_ip_space.text)
    sif = new_space_return["result"]
    ip_space_keys[sif['name']] = sif['id'] 
    return sif


with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
    futures = []
    for payload in payloads:
        futures.append(executor.submit(fetch, payload=payload))
    for future in concurrent.futures.as_completed(futures):
        print(future.result())

print(ip_space_keys)

sample = open('samplefile.txt', 'w')

sif = {}
with open('your_export.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
        if line_count == 0:
            line_count += 1
        else:
            if "dhcprange" == row[0]:
                line_count += 1
                x = ip_space_keys[row[35]]
                start = row[3]
                end = row[1]
                range_site = row[53]
                payload = {'payload': {'start': start, 'end': end, 'space': x, 'tags':{'Site': range_site}}}
                obj = {'object': 'ipam/range'}
                print(payload)
                sif[line_count] =payload,obj
    print(f'Processed {line_count} DHCP Ranges.')
csv_file.close()


def b1ddi(payload, object):
    url_ipam = "https://csp.infoblox.com/api/ddi/v1/"
    url = url_ipam + object
    create_ip_space = requests.request("post", url , headers=headers, json = payload)
    new_space_return = json.loads(create_ip_space.text)
    if "result" not in new_space_return:
        logging.error(f"{payload} - {new_space_return}")
        return dict()
    sif = new_space_return["result"]
    ip_space_keys[sif['name']] = sif['id']
    logging.info(f'Created - {payload} - {sif}')
    return sif

with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    futures = []
    for key, value in sif.items():
        futures.append(executor.submit(b1ddi, payload=value[0]['payload'],object=value[1]['object']))
    for future in concurrent.futures.as_completed(futures):
        print(future.result())


t2 = time.perf_counter() - t
print(f'Toal time taken: {t2:0.2f} seconds')
print(t,t2)

