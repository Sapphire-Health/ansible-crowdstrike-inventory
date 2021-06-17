## Build/Test Instructions

```
#Rough notes
cd ~/inventory/sapphire/crowdstrike
ansible-galaxy collection build -f --output-path build
rm -Rf ~/.ansible/collections/ansible_collections/sapphire
ansible-galaxy collection install build/sapphire-crowdstrike-1.0.0.tar.gz
#tar.gz file needs to be uploaded to GitHub as a release
ansible-doc -t inventory sapphire.crowdstrike.get_hosts
#ansible-doc -t inventory -l
ansible-inventory --list -i inventory.yml


ansible-galaxy collection install -r collections/requirements.yml

python3 plugins/inventory/get_hosts.py
```

### References:
- https://developers.redhat.com/blog/2021/03/10/write-your-own-red-hat-ansible-tower-inventory-plugin

### To do:
* Update Crowdstrike remote command script to use the inventory and run commands on a group of hosts
* Allow inventory.yml configuration to dynamically specify host variables to be used as groups
* Improve error handling using ansible.errors error handler. Ex: https://termlen0.github.io/2019/11/16/observations/
* Improve documentation
* Publish to Ansible Galaxy
* Enable caching https://docs.ansible.com/ansible/latest/dev_guide/developing_inventory.html#inventory-cache