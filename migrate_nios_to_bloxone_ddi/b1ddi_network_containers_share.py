#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'sifbaksh@gmail.com'

import csv
import requests
import json
import concurrent.futures
import time
import logging

# for logging events
logging.basicConfig(filename='logs.log', level=logging.DEBUG)

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
  'Authorization': 'Token MYTOKEN',
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

# convet the response to JSON
data = json.loads(response.text)

# Remove the IP Space that are already created
for entry in data['results']:
    # add item
    ip_space_keys[entry['name']] = entry['id']
    if entry['name'] in auxiliaryList:
        print(entry['name'])
        auxiliaryList.remove(entry['name'])

# Add the new ip_space to the payload to create new ip_space
payloads = []
for new_ip_space in auxiliaryList:
     payloads.append({'name':new_ip_space, 'tags':{'sif':'Yes'}})

# This will create the new ip_space when it's called from the ThreadPoolExecutor
def create_ip_space(payload):
    cis= requests.request("post", url_ip_space , headers=headers, json = payload)
    new_space_return = json.loads(cis.text)
    sif = new_space_return["result"]
    ip_space_keys[sif['name']] = sif['id'] 
    return sif

# This will start the creation of ip_space with 50 workers, I've tested to 100
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    futures = []
    for payload in payloads:
        futures.append(executor.submit(create_ip_space, payload=payload))
    for future in concurrent.futures.as_completed(futures):
        print(future.result())

# This will loop through the entire CSV file looking for row[0] that starts with "networkcontainer"
# Then stuff in "sif" key value pair
sif = {}
with open('your_export.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
        if line_count == 0:
            line_count += 1
        else:
            if "networkcontainer" == row[0]:
                line_count += 1
                # Please pay attention to this area, depending on your data it will change
                # NOTE - that when counting rows in python it starts at "0"
                # Use this link to you help, just -1 from it
                # https://www.vishalon.net/blog/excel-column-letter-to-number-quick-reference
                #
                # x is looking for the "network_view"
                x = ip_space_keys[row[28]]
                # nc_site is looking for an EA-Site in the CSV
                nc_site = row[52]
                address = row[1] + '/' + row[2]
                payload = {'payload': {'address': address, 'space': x, 'tags':{'Site':nc_site}}}
                # obj is the API path
                obj = {'object': 'ipam/address_block'}
                sif[line_count] =payload,obj
    print(f'Processed {line_count} network containers.')
csv_file.close()

# This function will create the new Address Block from Network Containers and when it's called from the ThreadPoolExecutor
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

# This will start the creation of ip_space with 50 workers, I've tested to 100
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    futures = []
    for key, value in sif.items():
        futures.append(executor.submit(b1ddi, payload=value[0]['payload'],object=value[1]['object']))
    for future in concurrent.futures.as_completed(futures):
        print(future.result())


t2 = time.perf_counter() - t
print(f'Toal time taken: {t2:0.2f} seconds')
print(t,t2)

