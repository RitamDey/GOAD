# elastic-edr

- Extension name : `elastic-edr`
- Compatibility : `*`
- Providers : ludus/virtualbox/vmware/vmware_esxi/proxmox/azure/aws
- Add a machine : elastic-edr (ip_range.53, 16GB RAM / 4 cpu)

- Kibana / Fleet is configured on http://{{ip_range}}.53:5601
- Elastic Stack 8.x (Elasticsearch + Kibana + Fleet) with the **Elastic Defend
  engine** (the `endpoint` integration, `EDRComplete` preset) + the `windows`
  integration (Sysmon / PowerShell / Defender winlog)
- Installs **Sysmon 14.14** + the **Elastic Agent** (MSI) on all domain windows
  machines and enrolls them in Fleet

This extension is the full attack / defend / purple team upgrade of the `elk`
extension. `elk` ships winlogbeat log aggregation, `elastic-edr` ships real
Fleet + EDR + Defend detection. Do not install both at the same time (both
install Sysmon).

## What gets deployed on each agent

- The Elastic Agent (Fleet managed, enrolls on Kibana :5601, events to ES :9200)
- Sysmon 14.14 with the SwiftOnSecurity sysmon-config v74 (EDR event source)
- The agent policy carries : `system`, Elastic Defend (`endpoint`, EDRComplete)
  and the `windows` integration limited to the `sysmon_operational`,
  `powershell_operational` and `windows_defender` streams

Sysmon is pinned to 14.x because 15.x dropped Windows Server 2016 support
(DC03 runs the 2016 template).

## License / feature levels

Self managed Kibana defaults to the **Basic** license: the EDR engine, malware
detection and the built-in SIEM rules work out of the box. Behavior /
ransomware / memory **prevention** need Platinum and auto-degrade on Basic
(detection is unaffected).

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
