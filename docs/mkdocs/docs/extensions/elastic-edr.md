# elastic-edr

- Extension name : `elastic-edr`
- Compatibility : `*`
- Providers : ludus/virtualbox/vmware/vmware_esxi/proxmox/azure/aws
- Add a machine : elastic-edr (ip_range.53, 16GB RAM / 4 cpu)

- Kibana / Fleet is configured on http://{{ip_range}}.53:5601
- Elastic Stack 8.x (Elasticsearch + Kibana + Fleet) with Endpoint Security (EDR) + Elastic Defend
- Install Sysmon + Elastic Agent on all domain windows machines (enrolled in Fleet)

This extension is the full attack / defend / purple team upgrade of the `elk`
extension. `elk` ships winlogbeat log aggregation, `elastic-edr` ships real
Fleet + EDR + Defend detection. Do not install both at the same time.

## Credentials (this is a lab)

| user          | password        |
|---------------|-----------------|
| elastic       | changeme-elastic    |
| kibana_system | changeme-kibana     |

## prerequisites

- 16GB RAM / 4 cpu / >= 80GB free disk on the ELASTIC-EDR machine

- On ludus prepare template :
```bash
ludus templates add -d ubuntu-22.04-x64-server
ludus templates build
```

- On proxmox you need an `Ubuntu_2204_x64` template (default id 922040)

## Install

- select your instance
```
load <instance_id>
```

- install the elastic-edr extension
```
install_extension elastic-edr
```

- The first run can take a few minutes (stack install + agent enrollment)

## Usage (purple team)

- Open Kibana : http://{{ip_range}}.53:5601 (elastic / changeme-elastic)
- Management -> Fleet : you should see the windows domain machines as agents
- Run a GOAD attack (e.g. mimikatz on SRV02, kerberoast, ...)
- Look for the generated alert in Kibana -> Security -> Alerts

## Uninstall

- Not implemented yet
