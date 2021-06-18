from ansible.plugins.inventory import BaseInventoryPlugin, to_safe_group_name
from datetime import datetime
import requests
import os
#import json
#import os.path
#from os import path

#source
#https://developers.redhat.com/blog/2021/03/10/write-your-own-red-hat-ansible-tower-inventory-plugin#making_the_plugin_work_in_ansible_tower

ANSIBLE_METADATA = {
    'metadata_version': '1.0.0',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: cs_inventory
plugin_type: inventory
short_description: Ansible inventory module for Crowdstrike Falcon API
version_added: "2.9.13"
description:
  - Ansible inventory module for Crowdstrike Falcon API
options:
  duplicates:
    description:
      - Whether the plugin should only return duplicate (stale) inventory items
    required: false
    type: bool
  group_by:
    description:
      - List of properties to use as Ansible groups
    required: false
    type: list
author:
  - Lyas Spiehler
'''


class InventoryModule(BaseInventoryPlugin):
    """An example inventory plugin."""

    GROUPS = []

    NAME = 'sapphire.crowdstrike.get_hosts'

    def verify_file(self, path):
        """Verify that the source file can be processed correctly.

        Parameters:
            path:AnyStr The path to the file that needs to be verified

        Returns:
            bool True if the file is valid, else False
        """
        # Unused, always return True
        return True

    def _get_raw_host_data(self):
        """Get the raw static data for the inventory hosts

        Returns:
            dict The host data formatted as expected for an Inventory Script
        """
        return {
            "all": {
                "hosts": ["web1.example.com", "web2.example.com"]
            },
            "_meta": {
                "hostvars": {
                    "web1.example.com": {
                        "ansible_user": "rdiscala"
                    },
                    "web2.example.com": {
                        "ansible_user": "rdiscala"
                    }
                }
            }
        }
    
    def _get_crowdstrike_hosts(self):

        #if path.exists("cache.json"):
            #print("Using cache")
        #    fcache = open("cache.json", "r")
        #    return json.loads(fcache.read())

        url = 'https://api.crowdstrike.com/oauth2/token'

        body = {
            'client_id': os.getenv("CSCLIENTID"),
            'client_secret': os.getenv("CSCLIENTSECRET")
        }

        headers = {
            'Accept' : 'application/json'
        }

        response = requests.post(url, data=body, headers=headers)

        access_token = None

        if response.status_code == 201:
            jsonresp = response.json()
            access_token = jsonresp["access_token"]
        else:
            moredata = False
            print("Error: Returned http status code " + str(response.status_code))
            exit

        max = 1000
        device_ids = []
        inventory = {
            'groups': [],
            'hosts': {},
            'duplicates': {}
        }

        group_by = self.GROUPS

        url = 'https://api.crowdstrike.com/devices/queries/devices-scroll/v1?limit=' + str(max)

        headers = {
            'Accept' : 'application/json',
            'Authorization': 'Bearer ' + access_token
        }

        moredata = True

        while moredata:
            response = requests.get(url, headers=headers)
            #print(response.headers)
            #print(response.status_code)
            #print(response.json())
            if response.status_code == 200:

                jsonresp = response.json()

                for resource in jsonresp["resources"]:
                    device_ids.append(resource)
                #print(len(device_ids))
                #print(jsonresp["meta"]["pagination"]["total"])
                if len(device_ids) < jsonresp["meta"]["pagination"]["total"]:
                    url = 'https://api.crowdstrike.com/devices/queries/devices-scroll/v1?offset=' + jsonresp["meta"]["pagination"]["offset"]
                else:
                    moredata = False
            else:
                moredata = False
                print("Error: Returned http status code " + str(response.status_code))

        #print(device_ids)
        #print(len(device_ids))

        index = 0
        numrequests = 0
        queue = []
        separator = "&ids="

        while index <= len(device_ids) - 1:
            queue.append(device_ids[index])
            if len(queue) % 100 == 0 or index == len(device_ids) - 1:
                numrequests = numrequests + 1
                #print("send " + str(len(queue)))
                #print(len(queue))
                url = 'https://api.crowdstrike.com/devices/entities/devices/v1?ids=' + separator.join(queue)
                queue = []
                response = requests.get(url, headers=headers)
                #print(response.headers)
                #print(response.status_code)
                if response.status_code == 200:
                    jsonresp = response.json()
                    #print("Print each key-value pair from JSON response")
                    #for key, value in jsonresp.items():
                    #    print(key)
                    if len(jsonresp["errors"]) == 0:
                        oudelim = ","
                        for resource in jsonresp["resources"]:
                            ou = None
                            if "ou" in resource.keys():
                                ou = oudelim.join(resource["ou"])
                            external_ip = None
                            if "external_ip" in resource.keys():
                                external_ip = resource["external_ip"]
                            local_ip = None
                            if "local_ip" in resource.keys():
                                local_ip = resource["local_ip"]
                            groups = []
                            if "groups" in resource.keys():
                                groups = resource["groups"]
                            tags = []
                            if "tags" in resource.keys():
                                tags = resource["tags"]
                            mac_address = None
                            if "mac_address" in resource.keys():
                                mac_address = resource["mac_address"]
                            reduced_functionality_mode = None
                            if "reduced_functionality_mode" in resource.keys():
                                reduced_functionality_mode = resource["reduced_functionality_mode"]
                            site_name = None
                            if "site_name" in resource.keys():
                                site_name = resource["site_name"]
                            hostname =  resource["hostname"].lower()
                            machine_domain = None
                            ansible_host = None
                            if "machine_domain" in resource.keys():
                                machine_domain = resource["machine_domain"]
                                ansible_host = resource["hostname"].lower() + '.' + resource["machine_domain"].lower()
                            else:
                                ansible_host = resource["hostname"].lower()
                            device = {
                                'device_id': resource["device_id"],
                                'cid': resource["cid"],
                                'ansible_host': ansible_host,
                                'hostname': hostname,
                                'domain': machine_domain,
                                'os': resource["os_version"],
                                'site_name': site_name,
                                'platform': resource["platform_name"],
                                'first_seen': resource["first_seen"],
                                'last_seen': resource["last_seen"],
                                'local_ip': local_ip,
                                'external_ip': external_ip,
                                'reduced_functionality_mode': reduced_functionality_mode,
                                'mac_address': mac_address,
                                'groups': groups,
                                'tags': tags,
                                'ou': ou,
                                'ansible_groups': []
                            }
                            if ansible_host in inventory["hosts"]:
                                existing = datetime.strptime(inventory["hosts"][ansible_host]["last_seen"], '%Y-%m-%dT%H:%M:%SZ')
                                duplicate = datetime.strptime(device["last_seen"], '%Y-%m-%dT%H:%M:%SZ')
                                #print(existing)
                                #print(duplicate)
                                if existing > duplicate:
                                    #print("existing is newer than duplicate")
                                    inventory["duplicates"][ansible_host] = device
                                else:
                                    #print("existing is older than duplicate")
                                    #print("using " + device["last_seen"])
                                    inventory["duplicates"][ansible_host] = inventory["hosts"][ansible_host]
                                    inventory["hosts"][ansible_host] = device
                            else:
                                inventory["hosts"][ansible_host] = device
                                for key in device.keys():
                                    #print(key)
                                    if key != 'ansible_groups' and key in group_by:
                                        if device[key] != None:
                                            if isinstance(device[key], list):
                                                for subkey in device[key]:
                                                    value = to_safe_group_name(subkey)
                                                    device["ansible_groups"].append(key + '_' + value)
                                                    if key + '_' + value not in inventory['groups']:
                                                        inventory['groups'].append(key + '_' + value)
                                            else:
                                                value =  to_safe_group_name(device[key])
                                                device["ansible_groups"].append(key + '_' + value)
                                                if key + '_' + value not in inventory['groups']:
                                                    inventory['groups'].append(key + '_' + value)
                            #print(host_groups)
                        #break
                else:
                    print("Error: Returned http status code " + str(response.status_code)) 
            index = index + 1
            #print(index)
        #cache data for testing        
        #f = open("cache.json", "a")
        #f.write(json.dumps(inventory))
        #f.close()
        return inventory

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path)
        self._read_config_data(path)
        duplicates = self.get_option("duplicates")
        group_by = self.get_option("group_by")
        if group_by:
            self.GROUPS = group_by
        #print(self.GROUPS)
        """Parse and populate the inventory with data about hosts.

        Parameters:
            inventory The inventory to populate

        We ignore the other parameters in the future signature, as we will
        not use them.

        Returns:
            None
        """
        inventorytype = "hosts"
        if duplicates:
            inventorytype = "duplicates"
        inventory = self._get_crowdstrike_hosts()
        for group in inventory["groups"]:
            self.inventory.add_group(group)
        for hostkey in inventory[inventorytype].keys():
            self.inventory.add_host(inventory[inventorytype][hostkey]["ansible_host"])
            #self.inventory.add_host(inventory[inventorytype][hostkey]["ansible_host"], group='all')
            if len(inventory[inventorytype][hostkey]["ansible_groups"]) > 0:
                for hostgroup in inventory[inventorytype][hostkey]["ansible_groups"]:
                    self.inventory.add_host(inventory[inventorytype][hostkey]["ansible_host"], group=hostgroup)
            for var_key, var_val in inventory[inventorytype][hostkey].items():
                if var_key != "ansible_groups":
                    self.inventory.set_variable(inventory[inventorytype][hostkey]["ansible_host"], var_key, var_val)
        '''
        groups = ['testa', 'testb']
        raw_data = self._get_raw_host_data()
        _meta = raw_data.pop('_meta')
        self.inventory.add_group('testa')
        self.inventory.add_group('testb')
        for group_name, group_data in raw_data.items():
            for host_name in group_data['hosts']:
                self.inventory.add_host(host_name, group='testa')
                self.inventory.add_host(host_name, group='testb')
                for var_key, var_val in _meta['hostvars'][host_name].items():
                    self.inventory.set_variable(host_name, var_key, var_val)
        '''

#Set environment variables and uncomment last 3 lines to test
#export CSCLIENTID=clientid
#export CSCLIENTSECRET=secret
#inventory = InventoryModule._get_crowdstrike_hosts(None)
#print(inventory["groups"])
#print(len(inventory["hosts"].keys()))
#print(len(inventory["duplicates"].keys()))

#uncomment to write data to file for examination, requires "import json"
#f = open("inventory_data.json", "a")
#f.write(json.dumps(inventory))
#f.close()