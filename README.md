## Build/Test Instructions

```
cd ~/inventory/sapphire/crowdstrike
ansible-galaxy collection build -f --output-path build
rm -Rf ~/.ansible/collections/ansible_collections/sapphire
ansible-galaxy collection install build/sapphire-crowdstrike-1.0.0.tar.gz
ansible-doc -t inventory sapphire.crowdstrike.get_hosts
#ansible-doc -t inventory -l
ansible-inventory --list -i inventory.yml


ansible-galaxy collection install -r collections/requirements.yml
```

### Source
https://developers.redhat.com/blog/2021/03/10/write-your-own-red-hat-ansible-tower-inventory-plugin