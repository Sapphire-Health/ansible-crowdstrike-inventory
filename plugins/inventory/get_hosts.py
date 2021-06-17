from ansible.plugins.inventory import BaseInventoryPlugin
import requests
import os
#import json

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
author:
    - Lyas Spiehler
'''


class InventoryModule(BaseInventoryPlugin):
    """An example inventory plugin."""

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
            'hosts': []
        }
        group_by = ['site_name', 'tags']

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
                            inventory['hosts'].append(device)
                            for key in device.keys():
                                #print(key)
                                if key != 'ansible_groups' and key in group_by:
                                    if device[key] != None:
                                        if isinstance(device[key], list):
                                            for subkey in device[key]:
                                                value = subkey.replace("/", "_").replace("-", "_")
                                                device["ansible_groups"].append(key + '_' + value)
                                                if key + '_' + value not in inventory['groups']:
                                                    inventory['groups'].append(key + '_' + value)
                                        else:
                                            value = device[key].replace("/", "_").replace("-", "_")
                                            device["ansible_groups"].append(key + '_' + value)
                                            if key + '_' + value not in inventory['groups']:
                                                inventory['groups'].append(key + '_' + value)
                            #print(host_groups)
                        #break
                else:
                    print("Error: Returned http status code " + str(response.status_code)) 
            index = index + 1
            #print(index)
                
        #send last bit if remaining
        #for key in host_groups.keys():
        #    print(key)
        #    print(len(host_groups[key]))
        #print(inventory["groups"])
        #print(len(inventory["hosts"]))
        return inventory

    group = ['test1', 'test2']

    def parse(self, inventory, *args, **kwargs):
        """Parse and populate the inventory with data about hosts.

        Parameters:
            inventory The inventory to populate

        We ignore the other parameters in the future signature, as we will
        not use them.

        Returns:
            None
        """
        # The following invocation supports Python 2 in case we are
        # still relying on it. Use the more convenient, pure Python 3 syntax
        # if you don't need it.
        super(InventoryModule, self).parse(inventory, *args, **kwargs)

        
        inventory = self._get_crowdstrike_hosts()
        for group in inventory["groups"]:
            self.inventory.add_group(group)
        for host in inventory["hosts"]:
            self.inventory.add_host(host["ansible_host"])
            if len(host["ansible_groups"]) > 0:
                for hostgroup in host["ansible_groups"]:
                    self.inventory.add_host(host["ansible_host"], group=hostgroup)
            for var_key, var_val in host.items():
                if var_key != "ansible_groups":
                    self.inventory.set_variable(host["ansible_host"], var_key, var_val)
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
#print(len(inventory["hosts"]))

#uncomment to write data to file for examination, requires "import json"
#f = open("inventory_data.json", "a")
#f.write(json.dumps(inventory))
#f.close()